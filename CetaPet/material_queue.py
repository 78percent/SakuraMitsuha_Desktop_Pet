"""Single in-flight QImage material job; latest request wins without a backlog."""
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QImage
from sakura_material import irregular_stealth


class _Renderer(QObject):
    finished = Signal(object)

    @Slot(object)
    def render(self, job):
        epoch, frame, progress, clock, regions = job
        try:
            result = irregular_stealth(frame, progress, clock, regions)
            self.finished.emit((epoch, result, None))
        except Exception as exc:
            self.finished.emit((epoch, None, str(exc)))


class MaterialQueue(QObject):
    requested = Signal(object)
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = QThread(self)
        self.renderer = _Renderer()
        self.renderer.moveToThread(self.thread)
        self.requested.connect(self.renderer.render)
        self.renderer.finished.connect(self._finished)
        self.thread.finished.connect(self.renderer.deleteLater)
        self.epoch = 0
        self.key = None
        self.pending = None
        self.busy = self.closed = False
        self.thread.start()

    def invalidate(self):
        self.epoch += 1
        self.key = None
        self.pending = None

    def submit(self, frame, progress, clock, regions, key):
        if self.closed:
            return
        if key != self.key:
            self.invalidate()
            self.key = key
        self.pending = (self.epoch, QImage(frame), progress, clock, regions)
        self._dispatch()

    def _dispatch(self):
        if not self.busy and self.pending is not None and not self.closed:
            job, self.pending = self.pending, None
            self.busy = True
            self.requested.emit(job)

    @Slot(object)
    def _finished(self, result):
        self.busy = False
        epoch, frame, error = result
        if not self.closed and epoch == self.epoch:
            if error is None:
                self.ready.emit(frame)
            else:
                self.failed.emit(error)
        self._dispatch()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.invalidate()
        self.thread.quit()
        # QImage-only work is bounded; finish it before destroying its QObject.
        self.thread.wait()
