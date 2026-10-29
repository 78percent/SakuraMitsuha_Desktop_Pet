"""Explicit runtime package contract. No discovery of artwork or staging exports."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
from typing import Protocol

from PySide6.QtGui import QImage, QImageReader


class PackageError(ValueError):
    pass


@dataclass(frozen=True)
class FrameRequest:
    height: int
    dpr: float
    elapsed: float = 0.0
    reaction: str = ''


class Presentation(Protocol):
    """GUI-thread owned, offscreen frames only; no windows/timers/input/services.

    Factory and first render must finish before installation. Failed factories
    own cleanup of partially allocated resources. close() must be idempotent.
    """
    def canvas_size(self, height: int) -> tuple[int, int]: ...
    def render(self, request: FrameRequest) -> QImage: ...
    def close(self) -> None: ...


def checked_frame(adapter, request):
    size = adapter.canvas_size(request.height)
    if (len(size) != 2 or any(type(n) is not int or not 1 <= n <= 2048 for n in size)
            or not math.isfinite(request.dpr) or not 0 < request.dpr <= 8):
        raise PackageError('呈现尺寸无效')
    frame = adapter.render(request)
    if (not isinstance(frame, QImage) or frame.isNull()
            or frame.format() != QImage.Format_ARGB32_Premultiplied
            or abs(frame.devicePixelRatio() - request.dpr) > .001
            or (frame.width(), frame.height()) != tuple(math.ceil(n * request.dpr) for n in size)):
        raise PackageError('呈现帧无效')
    return frame, size


def _json(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (OSError, ValueError) as exc:
        raise PackageError('模型配置损坏或缺失') from exc


def validate_package(folder):
    root = Path(folder).resolve()
    manifest = _json(root / 'manifest.json')
    if (manifest.get('schema_version') != 1 or manifest.get('id') != 'realistic'
            or manifest.get('status') != 'runtime-ready'
            or manifest.get('adapter') != 'cubism-v11-frames-v1'):
        raise PackageError('Live2D版尚未就绪')
    capabilities = manifest.get('capabilities', {})
    if (not isinstance(capabilities, dict) or capabilities.get('basic_visibility') is not True
            or type(capabilities.get('water_mist')) is not bool
            or (capabilities['water_mist'] and
                capabilities.get('water_mist_provider') != 'host-shared-v1')):
        raise PackageError('模型能力声明不兼容')
    acceptance = manifest.get('acceptance', {})
    if (not isinstance(acceptance, dict) or acceptance.get('integration_authorized') is not True
            or acceptance.get('runtime_verified') is not True):
        raise PackageError('Live2D版尚未完成运行验证')
    hashes = manifest.get('files', {})
    if not isinstance(hashes, dict) or not hashes:
        raise PackageError('模型缺少资源清单')

    def resource(name):
        if (not isinstance(name, str) or not name or '\\' in name
                or PureWindowsPath(name).drive or ':' in name):
            raise PackageError('模型资源路径无效')
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or name not in hashes:
            raise PackageError('模型资源缺失或越界')
        return path

    for name, digest in hashes.items():
        path = resource(name)
        if (not isinstance(digest, str) or len(digest) != 64
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise PackageError('模型资源校验失败')
    resource(acceptance.get('evidence'))
    model_path = resource(manifest.get('model'))
    model = _json(model_path)
    refs = model.get('FileReferences', {})
    if not isinstance(refs, dict):
        raise PackageError('模型引用无效')
    # model3 dependencies are relative to model3, not necessarily the package root.
    def dependency(name):
        if not isinstance(name, str) or '\\' in name or PureWindowsPath(name).drive or ':' in name:
            raise PackageError('模型引用无效')
        path = (model_path.parent / name).resolve()
        if not path.is_relative_to(root):
            raise PackageError('模型引用越界')
        return resource(path.relative_to(root).as_posix())

    moc = dependency(refs.get('Moc'))
    if moc.read_bytes()[:4] != b'MOC3':
        raise PackageError('MOC3 文件损坏')
    textures = refs.get('Textures')
    if not isinstance(textures, list) or not textures:
        raise PackageError('模型缺少纹理')
    for name in textures:
        if QImage(str(dependency(name))).isNull():
            raise PackageError('模型纹理损坏')
    for key in ('Physics', 'Pose', 'DisplayInfo', 'UserData'):
        if key in refs:
            _json(dependency(refs[key]))
    for item in refs.get('Expressions', []):
        _json(dependency(item['File']))
    referenced_motions = set()
    for group in refs.get('Motions', {}).values():
        for item in group:
            path = dependency(item['File'])
            _json(path)
            referenced_motions.add(path.relative_to(root).as_posix())
            if 'Sound' in item:
                dependency(item['Sound'])
    animation = manifest.get('animation', {})
    if (not isinstance(animation, dict) or animation.get('kind') != 'sdk-rendered-loop'
            or type(animation.get('fps')) is not int or animation['fps'] != 30
            or type(animation.get('frames')) is not int or animation['frames'] != 180):
        raise PackageError('待机动画声明无效')
    rows = json.loads(resource(animation.get('file')).read_text(encoding='utf-8'))
    if (not isinstance(rows, list) or len(rows) != 181
            or any(not isinstance(row, dict) or not isinstance(row.get('parameters'), dict)
                   for row in rows)):
        raise PackageError('待机动画轨迹无效')
    for row in rows:
        if any(not isinstance(key, str) or not isinstance(value, (int, float))
               or not math.isfinite(value) for key, value in row['parameters'].items()):
            raise PackageError('待机动画参数无效')
    preview = resource(animation.get('preview'))
    reader = QImageReader(str(preview))
    if not reader.supportsAnimation() or reader.imageCount() != 181:
        raise PackageError('v11 动画帧文件无效')
    return manifest


class PackageRegistry:
    def __init__(self, root, factories=None):
        self.root = Path(root)
        # Deliberately empty in production until a real adapter is integrated.
        self.factories = dict(factories or {})
        self._known_files = ()
        self._pending = self._executor = None
        # Pay the initial verification cost at configuration, before interaction.
        self._accept_status(self._validate_status())

    def _signature(self):
        # Stat only the already validated paths; never read textures in a menu.
        paths = [self.root/'manifest.json', *(self.root/name for name in self._known_files)]
        result = []
        for path in paths:
            try:
                st = path.stat()
                result.append((st.st_size, st.st_mtime_ns, st.st_ctime_ns))
            except OSError:
                result.append(None)
        return tuple(result)

    def _validate_status(self):
        try:
            manifest = validate_package(self.root)
            return manifest, ''
        except Exception:
            return None, '资源未就绪' if (self.root/'manifest.json').is_file() else '制作中'

    def _accept_status(self, result):
        self._manifest, self._reason = result
        if self._manifest is not None:
            self._known_files = tuple(self._manifest['files'])
        else:
            # Also notice repair of a resource in an otherwise invalid package.
            try:
                names = _json(self.root/'manifest.json').get('files', {})
                root = self.root.resolve()
                self._known_files = tuple(name for name in names if isinstance(name,str)
                    and (root/name).resolve().is_relative_to(root))
            except (OSError, ValueError, TypeError):
                self._known_files = ()
        self._stamp = self._signature()

    def availability(self):
        stamp = self._signature()
        if self._pending is not None and self._pending.done():
            result = self._pending.result()
            self._pending = None
            if stamp == self._pending_stamp:
                self._accept_status(result)
        if stamp != self._stamp:
            if self._pending is None:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='model-check')
                self._pending_stamp = stamp
                self._pending = self._executor.submit(self._validate_status)
            return False, '资源检查中'
        if self._manifest is None:
            return False, self._reason
        if self._manifest['adapter'] not in self.factories:
            return False, '呈现适配未就绪'
        return True, ''

    def prepare(self):
        # Revalidate at load time: resources may have changed since sidebar opened.
        manifest = validate_package(self.root)
        self._accept_status((manifest, ''))
        factory = self.factories.get(manifest['adapter'])
        if factory is None:
            raise PackageError('呈现适配未就绪')
        return factory(self.root, manifest)
