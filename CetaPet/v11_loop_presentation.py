"""Safe desktop playback of frames rendered from the v11 Cubism model."""
import math
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader

from model_packages import PackageError
from stealth_regions import V11_REGIONS


class V11LoopPresentation:
    background_material = True

    def __init__(self, root, manifest):
        self.path = Path(root) / manifest['animation']['preview']
        self.fps = manifest['animation']['fps']
        self.frame_count = manifest['animation']['frames']
        self.reader = None
        self.index = -1
        self.current = None
        self._frames = {}
        self._cache_key = None
        self._cache_limit = 336 * 1024 * 1024
        self._reset()

    def _scaled(self, frame, pixels, dpr):
        result = frame.scaled(*pixels, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        result = result.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        result.setDevicePixelRatio(dpr)
        return result

    def _reset(self):
        self.reader = QImageReader(str(self.path))
        if not self.reader.supportsAnimation() or self.reader.imageCount() < self.frame_count:
            raise PackageError('v11 动画文件无效')
        self.index = -1

    @staticmethod
    def canvas_size(height):
        return math.ceil(height * 720 / 900), math.ceil(height * 1000 / 900)

    def render(self, request):
        target = int(max(0, request.elapsed) * self.fps) % self.frame_count
        size = self.canvas_size(request.height)
        pixels = tuple(math.ceil(n * request.dpr) for n in size)
        key = (*pixels, request.dpr)
        if self._cache_key != key:
            self._frames.clear()
            self._cache_key = key
        if target in self._frames:
            return QImage(self._frames[target])
        capacity = self._cache_limit // (pixels[0]*pixels[1]*4)
        if target < self.index:
            self._reset()
        while self.index < target:
            frame = self.reader.read()
            if frame.isNull():
                raise PackageError('v11 动画解码失败')
            self.index += 1
            self.current = frame
            # Keep a fixed prefix when an entire large loop will not fit; an LRU
            # smaller than a sequential loop would evict every useful frame.
            if self.index < capacity:
                self._frames[self.index] = self._scaled(frame, pixels, request.dpr)
        if self.current is None:
            self.current = self.reader.read()
            if self.current.isNull():
                raise PackageError('v11 动画首帧无效')
            self.index = 0
        if target in self._frames:
            return QImage(self._frames[target])
        return self._scaled(self.current, pixels, request.dpr)

    def close(self):
        self._frames.clear()
        self.reader = None
        self.current = None

    def stealth_regions(self):
        """Envelopes for this loop; future adapters may return per-frame regions."""
        return V11_REGIONS
