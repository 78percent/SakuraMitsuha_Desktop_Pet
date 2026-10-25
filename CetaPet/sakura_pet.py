"""Restored V3 front rig with the current irregular mirage material. V4 draft is commented out and disconnected."""
import math,time
from PySide6.QtCore import QPoint,Qt,QTimer
from PySide6.QtGui import QAction,QActionGroup,QIcon,QPainter
from PySide6.QtWidgets import QApplication,QMenu,QPushButton,QSystemTrayIcon,QWidget
from sakura_animation import DEFAULT_CHARACTER_HEIGHT, ACTION_LABELS,EXPRESSIONS,GESTURES_ENABLED,Motion,SakuraRig,ripple

class GhostOverlay(QWidget):
    def __init__(self,owner):
        super().__init__(None,Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowTransparentForInput|Qt.WindowDoesNotAcceptFocus)
        self.owner=owner
        self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_TransparentForMouseEvents);self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowTitle('三叶 · 极淡残影')
    def paintEvent(self,event):
        if self.owner._frame is not None:
            p=QPainter(self);p.drawImage(0,0,self.owner._frame);p.end()

def create_sakura_pet(base):
    class SakuraPet(base):
        is_sakura=True
        def __init__(self):
            super().__init__();self.setWindowTitle('佐仓三叶')
            self._rig=SakuraRig();self._motion=Motion();self._character_height=DEFAULT_CHARACTER_HEIGHT
            self._fade=0.;self._transition='';self._manual_hold=False;self._frame=None;self._cleaned=False
            self._click_timer.setTimerType(Qt.PreciseTimer)
            self._click_timer.setInterval(QApplication.doubleClickInterval())
            self._last_tick=time.perf_counter();self._restore_button=None;self._ghost=GhostOverlay(self)
            self._auto_restore=QTimer(self);self._auto_restore.setSingleShot(True);self._auto_restore.timeout.connect(self.appear)
            self._frame_timer=QTimer(self);self._frame_timer.setTimerType(Qt.PreciseTimer);self._frame_timer.setInterval(33);self._frame_timer.timeout.connect(self._animation_tick)
            self._resize_character(DEFAULT_CHARACTER_HEIGHT);self._home_rect=self._compute_center_geometry()

        def play_entrance(self):
            self._cheerup_timer.stop();self._idle_start();self._fade=1.;self.appear();return True

        def _idle_eligible(self):
            chat=self._chat_window is not None and self._chat_window.isVisible()
            return self._fade==0 and not self._transition and self._state=='idle' and not self._pressing and self.isVisible() and not chat and QApplication.activePopupWidget() is None and QApplication.activeModalWidget() is None

        def _animation_tick(self):
            now=time.perf_counter();dt=max(0,now-self._last_tick);self._last_tick=now
            if self._motion.tick(dt,self._idle_eligible(),self._state):self.vanish(False)
            if self._transition=='vanish':self._fade=min(1.,self._fade+dt/1.6)
            elif self._transition=='appear':self._fade=max(0.,self._fade-dt/1.6)
            self._refresh_frame()
            if self._transition=='vanish' and self._fade>=1:
                self._transition='';self.hide();self._ghost.setGeometry(self.geometry());self._ghost.show();self._ghost.update()
                self._frame_timer.setInterval(33)
                if not self._manual_hold:self._auto_restore.start(round(self._motion.rng.uniform(3000,5000)))
                self._show_recovery_if_needed()
            elif self._transition=='appear' and self._fade<=0:
                self._transition='';self._ghost.hide();self._back_to_idle();self._frame_timer.setInterval(33)

        def _refresh_frame(self):
            if not hasattr(self,'_rig'):return
            reaction=self._state if self._state in ('touch','pickup','query') else ''
            frame=self._rig.render(self._motion.pose(reaction),self._character_height,self.devicePixelRatioF())
            self._frame=ripple(frame,self._fade,self._motion.time,revealing=self._transition=='appear') if self._fade>0 else frame
            self._ghost.setGeometry(self.geometry());self._ghost.update();self.update()

        def _resize_character(self,height):
            old=self.geometry().bottomLeft();self._character_height=int(height)
            self.resize(math.ceil(height*720/900),math.ceil(height*1000/900))
            if hasattr(self,'_home_rect'):self.move(self._clamp_pos(QPoint(old.x(),old.y()-self.height()+1)))
            if self._bubble:self._bubble.place_above(self)
            self._refresh_frame()

        def vanish(self,manual=True):
            if not manual and not self._idle_eligible():return
            self._manual_hold=manual or self._manual_hold
            if manual:self._auto_restore.stop()
            if self._fade>=1 and not self._transition:return
            self._click_timer.stop();self._pressing=self._drag_active=False;self._drag_offset=None;self._kill_bubble();self._pause_idle()
            self._transition='vanish';self._start_animation_timer()

        def appear(self):
            self._auto_restore.stop();self._manual_hold=False
            if self._restore_button is not None:self._restore_button.hide()
            self._ghost.hide();self._transition='appear' if self._fade>0 else ''
            self._refresh_frame();self.show();self.raise_();self._start_animation_timer()
            if self._fade==0:self._back_to_idle()

        def preview_expression(self,expression):
            self.appear();self._motion.trigger_expression(expression)

        def preview_blink(self):
            self.appear();self._motion.blink_start=self._motion.time;self._motion.blink_at=self._motion.time+4

        def preview_invisibility(self):
            self.vanish(False)

        def preview_walk(self,*args):
            return  # DISABLED: V4 locomotion is not an active entry point.

        def preview_crouch(self,*args):
            return  # DISABLED: V4 Q/fear module is not an active entry point.

        def hideEvent(self,event):
            if hasattr(self,'_frame_timer') and self._fade==0:self._frame_timer.stop()
            super().hideEvent(event)

        def _cleanup(self):
            if self._cleaned:return
            self._cleaned=True;self._frame_timer.stop();self._auto_restore.stop();self._ghost.hide();self._ghost.deleteLater()
            if self._restore_button is not None:self._restore_button.hide();self._restore_button.deleteLater();self._restore_button=None
            super()._cleanup()

        def _set_image(self, key):
            if not hasattr(self, '_rig'):
                return super()._set_image(key)
            self._cur_key = key
            # External state changes keep the same model, never flash whale artwork.
            self.update()

        def _start_stage_timer(self, ms):
            self._stage_remaining = ms

        def _start_nothing_timer(self):
            pass

        def _idle_start(self):
            self._idle_started = True
            self._idle_paused = False
            self._stage_idx = 0
            self._state = 'idle'
            self._cur_key = 'nothing'

        def _clamp_pos(self, pos):
            center = pos + QPoint(self.width()//2, self.height()//2)
            screen = QApplication.screenAt(center) or self.screen() or QApplication.primaryScreen()
            if screen is None:
                return pos
            area = screen.availableGeometry()
            return QPoint(max(area.left(),min(pos.x(),max(area.left(),area.right()-self.width()+1))),
                          max(area.top(),min(pos.y(),max(area.top(),area.bottom()-self.height()+1))))

        def wheelEvent(self, event):
            if event.modifiers() & Qt.ControlModifier:
                step = 30 if event.angleDelta().y() > 0 else -30
                self._resize_character(max(180, min(720, self._character_height+step)))
                event.accept()
            else:
                super().wheelEvent(event)

        def mouseDoubleClickEvent(self, event):
            if event.button() != Qt.LeftButton:
                return super().mouseDoubleClickEvent(event)
            if self._drag_active:
                event.accept()
                return
            # Cancel the delayed first click and consume the second release.
            self._suppress_next_release = True
            self.vanish(manual=True)
            event.accept()

        def mouseReleaseEvent(self, event):
            if event.button() == Qt.LeftButton and self._suppress_next_release:
                self._suppress_next_release = False
                self._pressing = self._drag_active = False
                self._drag_offset = None
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def hide_whale(self):
            self.vanish(manual=True)

        def show_whale(self, greet=True):
            self.appear()

        def toggle_hide_whale(self):
            if self._toggle_would_reveal():
                self.appear()
            else:
                self.vanish(manual=True)

        def _toggle_would_reveal(self):
            # Use the current destination even before the first animation tick.
            return self._transition != 'appear' and (
                self._transition == 'vanish' or self._fade > 0
                or self.isHidden() or self._manual_hold)

        def _on_tray_activated(self, reason):
            if reason == QSystemTrayIcon.DoubleClick:
                self.toggle_hide_whale()

        def _ensure_visible_for_action(self):
            if self.isHidden() or self._fade > 0 or self._manual_hold:
                self.appear()

        def _show_speech(self, text):
            if not hasattr(self, '_fade') or self._fade == 0:
                super()._show_speech(text)

        def open_chat_window(self):
            super().open_chat_window()
            self._chat_window.setWindowTitle('与三叶聊天')

        def _do_touch(self):
            if self._transition:
                return
            super()._do_touch()

        def _start_pickup(self):
            if self._transition:
                return
            super()._start_pickup()

        def preview_action(self, action):
            if not GESTURES_ENABLED:
                return
            self.appear()
            if self._state != 'idle':
                return
            self._motion.trigger(action)

        def _show_recovery_if_needed(self):
            if self._tray is not None or not self._manual_hold:
                return
            if self._restore_button is None:
                self._restore_button = QPushButton('三叶 · 现形')
                self._restore_button.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
                self._restore_button.clicked.connect(self.appear)
            self._restore_button.move(self._clamp_pos(self.pos()))
            self._restore_button.show()

        def create_tray(self):
            tray = QSystemTrayIcon(self)
            icon = self._rig.layers['head_open']
            tray.setIcon(QIcon(icon))
            tray.setToolTip('佐仓三叶 · 双击切换隐身／现形，右键打开菜单')
            menu = QMenu()
            def rebuild():
                replacement = self._build_context_menu()
                menu.clear()
                # Keep action ownership alive until the next rebuild.
                old = getattr(tray, '_source_menu', None)
                tray._source_menu = replacement
                for action in replacement.actions():
                    menu.addAction(action)
                if old is not None:
                    old.deleteLater()
            menu.aboutToShow.connect(rebuild)
            rebuild()
            tray.setContextMenu(menu)
            tray._menu = menu
            tray.activated.connect(self._on_tray_activated)
            tray.show()
            return tray

        def contextMenuEvent(self, event):
            menu = self._build_context_menu()
            try:
                menu.exec(event.globalPos())
            finally:
                menu.deleteLater()
            event.accept()

        def _start_animation_timer(self):
            self._last_tick = time.perf_counter()
            self._frame_timer.setInterval(33)
            self._frame_timer.start()

        def paintEvent(self, event):
            if not hasattr(self, '_rig'):
                return super().paintEvent(event)
            painter = QPainter(self)
            if self._frame is not None:
                painter.drawImage(0, 0, self._frame)
            painter.end()

        def showEvent(self, event):
            super().showEvent(event)
            if hasattr(self, '_frame_timer'):
                self._start_animation_timer()

        def _build_context_menu(self):
            menu = QMenu(self)
            menu.addAction('与三叶聊天').triggered.connect(self.open_chat_window)

            documents = menu.addMenu('资料')
            documents.addAction('导入资料…').triggered.connect(self.start_add_documents)
            documents.addAction('打开资料文件夹').triggered.connect(self.start_view_files)
            api = menu.addMenu('DeepSeek')
            api.addAction('查询余额').triggered.connect(self.start_query)
            api.addAction('设置 API 密钥…').triggered.connect(self.change_api_key)
            menu.addSeparator()

            size = menu.addMenu('角色大小')
            group = QActionGroup(size)
            group.setExclusive(True)
            for height in (180, 260, 360, 480, 600, 720):
                action = size.addAction(f'{height} 像素')
                action.setCheckable(True)
                action.setChecked(height == self._character_height)
                group.addAction(action)
                action.triggered.connect(lambda checked=False, value=height: self._resize_character(value))

            expressions = menu.addMenu('表情')
            for key, label in EXPRESSIONS.items():
                expressions.addAction(label).triggered.connect(
                    lambda checked=False, expression=key: self.preview_expression(expression))
            preview = menu.addMenu('动作预览')
            for key, label in (ACTION_LABELS.items() if GESTURES_ENABLED else ()):
                preview.addAction(label).triggered.connect(lambda checked=False, action=key: self.preview_action(action))
            preview.addAction('眨眼').triggered.connect(self.preview_blink)
            preview.addAction('隐身后自动现形').triggered.connect(self.preview_invisibility)
            auto = menu.addAction('待机自动隐身')
            auto.setToolTip('空闲 15～30 分钟后短暂隐身，再自动现形')
            auto.setCheckable(True)
            auto.setChecked(self._motion.easter_enabled)
            auto.toggled.connect(lambda enabled: setattr(self._motion, 'easter_enabled', enabled))
            menu.addSeparator()

            menu.addAction('重置位置').triggered.connect(self.reset_position)
            menu.addAction('现形' if self._toggle_would_reveal() else '隐身').triggered.connect(self.toggle_hide_whale)
            menu.addSeparator()
            menu.addAction('退出').triggered.connect(self.quit_app)
            return menu

    return SakuraPet
