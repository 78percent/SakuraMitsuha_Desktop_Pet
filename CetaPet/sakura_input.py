# DISABLED 2026-10-20: 用户要求整轮回退，禁止导入启用。
# Original preserved in disabled_v4/sakura_input.py.disabled
# """A single-pose silhouette shared by the displayed frame and native input region."""
# from PySide6.QtCore import Qt, QPoint, Signal
# from PySide6.QtGui import QBitmap, QImage, QPainter, QRegion
# from PySide6.QtWidgets import QWidget
# 
# 
# def body_region(coverage: QImage) -> QRegion:
#     """Use unattenuated coverage, never the almost invisible rendered alpha."""
#     dpr=coverage.devicePixelRatio()
#     logical=coverage.scaled(round(coverage.width()/dpr),round(coverage.height()/dpr))
#     logical.setDevicePixelRatio(1)
#     bitmap=QBitmap.fromImage(logical.createAlphaMask(Qt.ThresholdDither|Qt.ThresholdAlphaDither|Qt.AvoidDither))
#     return QRegion(bitmap)
# 
# 
# class BodySurface(QWidget):
#     clicked=Signal()
#     released=Signal()
#     def __init__(self, interactive=False):
#         flags=Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus
#         if not interactive:flags|=Qt.WindowTransparentForInput
#         super().__init__(None,flags)
#         self.interactive=interactive
#         self.frame=None;self.region=QRegion();self.pressed=False;self.fired=False
#         self.setAttribute(Qt.WA_TranslucentBackground)
#         self.setAttribute(Qt.WA_ShowWithoutActivating)
#         self.setAttribute(Qt.WA_TransparentForMouseEvents,not interactive)
#         self.setWindowTitle('三叶 · 身体交互' if interactive else '三叶 · 隐身身体')
#     def set_frame(self, frame, coverage):
#         self.frame=frame
#         self.resize(round(frame.width()/frame.devicePixelRatio()),round(frame.height()/frame.devicePixelRatio()))
#         if self.interactive:
#             self.region=body_region(coverage);self.setMask(self.region)
#         self.update()
#     def arm(self):
#         self.pressed=self.fired=False
#         self.show();self.raise_()
#     def paintEvent(self,event):
#         if self.frame is not None:
#             p=QPainter(self);p.drawImage(0,0,self.frame);p.end()
#     def mousePressEvent(self,event):
#         self.pressed=event.button()==Qt.LeftButton and self.region.contains(event.position().toPoint())
#         if self.pressed:self.grabMouse()
#         event.accept()
#     def mouseReleaseEvent(self,event):
#         valid=self.pressed and event.button()==Qt.LeftButton and self.region.contains(event.position().toPoint())
#         self.pressed=False;event.accept()
#         if self.mouseGrabber() is self:self.releaseMouse()
#         if valid and not self.fired:
#             self.fired=True;self.clicked.emit()
#         self.released.emit()
#     def mouseDoubleClickEvent(self,event):
#         # A discovered body's second click cannot restart its story.
#         self.pressed=False;event.accept()
