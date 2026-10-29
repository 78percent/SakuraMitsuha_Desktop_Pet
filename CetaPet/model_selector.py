"""Compact selector and transactional presentation swap on one persistent host."""
import math
import time

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QFont, QImage
from PySide6.QtWidgets import QDialog, QLabel, QRadioButton, QVBoxLayout, QButtonGroup

from character_config import CharacterConfig
from model_packages import FrameRequest, checked_frame
from stealth_regions import GENERIC_REGIONS


class ModelSidebar(QDialog):
    def __init__(self, host):
        super().__init__(host, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.host = host
        self.setWindowTitle('角色')
        self.setFont(QFont('Microsoft YaHei', 10))
        self.setMinimumWidth(208)
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        self.group = QButtonGroup(self)
        self.buttons = {}
        for model, label in (('q', 'Q版'), ('realistic', '写实版')):
            button = QRadioButton(label)
            button.setMinimumHeight(44)
            button.setAccessibleName(label)
            self.group.addButton(button)
            layout.addWidget(button)
            self.buttons[model] = button
            button.clicked.connect(lambda checked=False, key=model: self.choose(key))
        # Only unavailable/error feedback; no duplicate title or explanatory prose.
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setAccessibleName('角色状态')
        layout.addWidget(self.message)
        self.sync()

    def sync(self):
        ready, reason = self.host._model_registry.availability()
        active = self.host._active_model
        for key, button in self.buttons.items():
            button.setChecked(key == active)
            button.setEnabled(not self.host._model_switching and (key == 'q' or ready))
        self.buttons['realistic'].setToolTip(reason)
        self.buttons['realistic'].setAccessibleDescription(reason)
        message = self.host._selector_notice or (f'写实版 · {reason}' if not ready else '')
        self.message.setText(message)
        self.message.setVisible(bool(message))
        self.adjustSize()

    def choose(self, key):
        self.buttons[self.host._active_model].setChecked(True)
        self.host.switch_model(key)
        self.sync()

    def open_at_pet(self):
        self.sync()
        self.adjustSize()
        host = self.host
        screen = host.screen()
        if screen:
            area = screen.availableGeometry()
            x = host.x() + host.width() + 8
            if x + self.width() > area.right() + 1:
                x = host.x() - self.width() - 8
            x = max(area.left(), min(x, area.right() - self.width() + 1))
            y = max(area.top(), min(host.y(), area.bottom() - self.height() + 1))
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self.buttons[self.host._active_model].setFocus(Qt.OtherFocusReason)


class ModelSelectorMixin:
    _active_model = 'q'
    _presentation = None
    _model_switching = False
    _selector = None
    _selector_notice = ''
    _model_config = None
    _render_recovery_pending = False

    def configure_models(self, config_path, registry):
        """Called once after legacy position restoration, before first show."""
        self._model_config = CharacterConfig(config_path)
        self._model_registry = registry
        saved = self._model_config.read()
        self._selector_notice = self._model_config.warning
        self._model_switching = True
        try:
            q = saved['geometry'].get('q')
            if q:
                self._resize_character(q['height'])
                self.move(self._clamp_pos(QPoint(q['x'], q['y'])))
        finally:
            self._model_switching = False
        if saved['selected'] == 'realistic' and not self.switch_model('realistic', startup=True):
            self._selector_notice = '写实版不可用，已恢复Q版'
            if not self._save_geometry():
                self._selector_notice += '；选择未能保存'

    def open_model_selector(self):
        if self._model_config is None:
            return
        if self._selector is None:
            self._selector = ModelSidebar(self)
        self._selector.open_at_pet()

    def _model_geometry(self):
        return dict(x=self.x(), y=self.y(), height=self._character_height)

    def _save_geometry(self):
        if self._model_config is None:
            return super()._save_geometry()
        if self._model_switching:
            return True
        try:
            self._model_config.update(self._active_model, {self._active_model: self._model_geometry()})
            return True
        except Exception:
            self._selector_notice = '位置或尺寸未能保存'
            return False

    def _prepare_q_frame(self, height):
        # Keep the exact existing rig/material pipeline. Do not replace motion state.
        frame = self._rig.render(self._motion.pose(), height, self.devicePixelRatioF())
        if frame.isNull() or any(layer.isNull() for layer in self._rig.layers.values()):
            raise ValueError('Q版资源不可用')
        return frame, (math.ceil(height * 720 / 900), math.ceil(height * 1000 / 900))

    def _install_presentation(self, key, adapter, frame, size, target):
        # No rendering/event pumping, input or services in this commit section.
        self._active_model = key
        self._presentation = adapter
        self._character_height = target['height']
        self._frame = frame
        self.resize(*size)
        self.move(self._clamp_pos(QPoint(target['x'], target['y'])))

    def switch_model(self, key, *, startup=False):
        if self._model_config is None or self._model_switching or key not in ('q', 'realistic'):
            return False
        if key == self._active_model:
            return True
        # A switch during a drag or material transition would lose input/ghost state.
        if self._pressing or self._transition:
            self._selector_notice = '请在拖拽或隐现结束后切换'
            return False
        self._model_switching = True
        candidate = None
        old = (self._active_model, self._presentation, self._frame, self.geometry(), self._character_height)
        previous_layout = self._model_geometry()
        installed = False
        try:
            saved = self._model_config.read()
            target = saved['geometry'].get(key, dict(x=self.x(), y=self.y(), height=180))
            if key == 'realistic':
                candidate = self._model_registry.prepare()
                frame, size = checked_frame(candidate, FrameRequest(target['height'], self.devicePixelRatioF()))
                rgba = frame.convertToFormat(QImage.Format_RGBA8888)
                if not any(rgba.constBits()[3::4]):
                    raise ValueError('模型首帧为空')
            else:
                frame, size = self._prepare_q_frame(target['height'])
            installed = True
            self._install_presentation(key, candidate, frame, size, target)
            # Save only after installation; atomic failure restores the old presentation.
            self._model_config.update(key, {old[0]: previous_layout, key: self._model_geometry()})
        except Exception:
            if installed:
                self._active_model, self._presentation, self._frame = old[:3]
                self._character_height = old[4]
                self.setGeometry(old[3])
            if candidate is not None:
                self._close_presentation(candidate)
            self._selector_notice = '切换失败，已保留当前角色'
            return False
        finally:
            self._model_switching = False
        # Only after commit may the old renderer release its resources.
        if old[1] is not None:
            self._close_presentation(old[1])
        was_hidden = not startup and (self.isHidden() or self._fade > 0 or self._manual_hold)
        self._auto_restore.stop()
        self._ghost.hide()
        self._fade = 1.0 if was_hidden else 0.0
        self._manual_hold = was_hidden
        self._presentation_started = time.perf_counter()
        self._selector_notice = ''
        if startup:
            return True  # main owns first show/entrance; no recovery window during preload.
        if was_hidden:
            self.hide()
            self._refresh_frame()
            self._ghost.setGeometry(self.geometry())
            self._ghost.show()
            self._start_animation_timer()
            self._show_recovery_if_needed()
        else:
            self._start_animation_timer()
            self.update()
        if self._bubble:
            self._bubble.place_above(self)
        if self._selector:
            self._selector.sync()
        return True

    @staticmethod
    def _close_presentation(adapter):
        try:
            adapter.close()
        except Exception:
            pass  # A disposal error cannot roll back an already committed switch.

    def _alternate_regions(self):
        provider = getattr(self._presentation, 'stealth_regions', None)
        return provider() if provider is not None else GENERIC_REGIONS

    def _refresh_alternate_frame(self):
        try:
            request = FrameRequest(self._character_height, self.devicePixelRatioF(),
                                   max(0., time.perf_counter() - self._presentation_started), self._state)
            frame, size = checked_frame(self._presentation, request)
            self._publish_frame(frame, self._alternate_regions())
        except Exception:
            # Retain the last good frame; recover outside paint/timer callbacks.
            if not self._render_recovery_pending:
                self._render_recovery_pending = True
                QTimer.singleShot(0, self, self._recover_presentation)

    def _recover_presentation(self):
        if self._cleaned:
            return
        self._render_recovery_pending = False
        if self._active_model == 'realistic':
            # Internal recovery may cross a transition; a user-initiated switch
            # still cannot. Keep the material destination and current progress.
            fade, transition, manual, hidden = self._fade, self._transition, self._manual_hold, self.isHidden()
            self._transition = ''
            self._pressing = self._drag_active = False
            self._drag_offset = None
            recovered = self.switch_model('q')
            self._fade, self._transition, self._manual_hold = fade, transition, manual
            if recovered:
                self._refresh_frame()
                if not hidden:
                    self._ghost.hide()
                    self.show()
                elif fade > 0:
                    self._ghost.show()
                self._start_animation_timer()
                if hidden and not manual and not transition:
                    self._auto_restore.start(round(self._motion.rng.uniform(3000,5000)))
            self._selector_notice = ('写实版呈现失败，已恢复Q版' if recovered
                                     else '呈现失败，保留最后画面；请切回Q版')
            if not recovered:
                self._frame_timer.stop()
            if self._selector:
                self._selector.sync()

    def _cleanup_selector(self):
        if self._selector:
            self._selector.hide()
            self._selector.deleteLater()
            self._selector = None
        if self._presentation is not None:
            self._close_presentation(self._presentation)
            self._presentation = None
