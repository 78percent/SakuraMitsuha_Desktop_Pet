"""Reproducible Qt interaction checks, with no personal data or remote API calls."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'CetaPet'))
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
import main
import runtime_config
from sakura_animation import PERSONA, EXPRESSIONS
from sakura_pet import create_sakura_pet


def actions(menu):
    result = {}
    for action in menu.actions():
        if action.menu():
            result.update(actions(action.menu()))
        elif not action.isSeparator():
            result[action.text()] = action
    return result


class SakuraPublicReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        folder = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.position = folder / 'config.json'
        for owner, name, value in (
            (main, 'CONFIG_PATH', str(self.position)),
            (main, 'RAG_DIR', str(folder / 'RAG')),
            (main, '_CURRENT_KEY', ''),
            (runtime_config, 'ENV_PATH', folder / '.env'),
        ):
            self.stack.enter_context(patch.object(owner, name, value))
        self.pet = create_sakura_pet(main.DesktopPet)()
        self.pet.show()
        self.pet.move(200, 200)
        self.pet._idle_start()
        self.pet._frame_timer.stop()
        self.pet._click_timer.setInterval(60)

    def tearDown(self):
        self.pet._cleanup()
        for widget in self.app.topLevelWidgets():
            widget.hide()
            widget.deleteLater()
        self.app.processEvents()

    def test_click_and_drag_are_quiet_and_save_position(self):
        point = QPoint(40, 40)
        with patch.object(self.pet, '_show_speech', wraps=self.pet._show_speech) as speak:
            QTest.mouseClick(self.pet, Qt.LeftButton, pos=point)
            QTest.qWait(100)
            self.assertEqual(self.pet._state, 'touch')
            self.assertTrue(self.pet._touch_timer.isActive())
            self.assertIsNone(self.pet._bubble)
            self.pet._on_touch_timeout()
            before = self.pet.pos()
            QTest.mousePress(self.pet, Qt.LeftButton, pos=point)
            target = self.pet.mapToGlobal(point) + QPoint(-40, -25)
            event = QMouseEvent(QEvent.MouseMove, QPointF(self.pet.mapFromGlobal(target)),
                                QPointF(target), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
            self.app.sendEvent(self.pet, event)
            self.assertEqual(self.pet._state, 'pickup')
            self.assertNotEqual(self.pet.pos(), before)
            self.assertIsNone(self.pet._bubble)
            QTest.mouseRelease(self.pet, Qt.LeftButton, pos=point)
            self.assertEqual(self.pet._state, 'idle')
            saved = json.loads(self.position.read_text())
            self.assertEqual((saved['window_x'], saved['window_y']), (self.pet.x(), self.pet.y()))
            speak.assert_not_called()

    def test_pet_and_tray_double_click_still_toggle_stealth(self):
        QTest.mouseDClick(self.pet, Qt.LeftButton, pos=QPoint(40, 40))
        QTest.mouseRelease(self.pet, Qt.LeftButton, pos=QPoint(40, 40))
        self.assertEqual(self.pet._transition, 'vanish')
        self.assertTrue(self.pet._manual_hold)
        self.pet._on_tray_activated(QSystemTrayIcon.DoubleClick)
        self.assertFalse(self.pet._manual_hold)
        self.assertTrue(self.pet.isVisible())

    def test_grouped_actions_keep_original_callbacks(self):
        callbacks = {
            '与三叶聊天': 'open_chat_window', '导入资料…': 'start_add_documents',
            '打开资料文件夹': 'start_view_files', '查询余额': 'start_query',
            '设置 API 密钥…': 'change_api_key', '重置位置': 'reset_position',
            '隐身': 'toggle_hide_whale', '退出': 'quit_app',
            '眨眼': 'preview_blink', '隐身后自动现形': 'preview_invisibility',
        }
        with ExitStack() as stack:
            spies = {label: stack.enter_context(patch.object(self.pet, name))
                     for label, name in callbacks.items()}
            menu = self.pet._build_context_menu()
            entries = actions(menu)
            for label, spy in spies.items():
                entries[label].trigger()
                spy.assert_called_once()
            entries['260 像素'].trigger()
            self.assertEqual(self.pet._character_height, 260)
            auto = entries['待机自动隐身']
            previous = self.pet._motion.easter_enabled
            auto.trigger()
            self.assertEqual(self.pet._motion.easter_enabled, not previous)
            for key, label in EXPRESSIONS.items():
                entries[label].trigger()
                self.assertEqual(self.pet._motion.preview_expression, key)
            self.assertFalse({'换脚站', '拨头发', '整理袖口'} & entries.keys())

    def test_tray_rebuild_uses_same_actions_and_current_stealth_state(self):
        with patch.object(QSystemTrayIcon, 'show'):
            tray = self.pet.create_tray()
        self.pet.attach_tray(tray)
        self.assertEqual(set(actions(tray._menu)), set(actions(self.pet._build_context_menu())))
        self.pet.vanish(manual=True)
        tray._menu.aboutToShow.emit()
        self.assertIn('现形', actions(tray._menu))
        self.assertNotIn('隐身', actions(tray._menu))

    def test_chat_identity_persona_and_reference_data_are_preserved(self):
        window = main.ChatWindow(self.pet)
        self.assertEqual(window.windowTitle(), '与三叶聊天')
        self.assertEqual(window._view.toPlainText(), '')
        self.assertTrue(window._rag_label.isHidden())
        self.pet.rag_text = 'A local reference.'
        self.pet.rag_loaded = len(self.pet.rag_text)
        window.update_rag_label()
        self.assertFalse(window._rag_label.isHidden())
        window._history = [{'role': 'user', 'content': 'Hello'}]
        messages = window._build_chat_messages()
        self.assertEqual(messages[0]['content'], PERSONA)
        self.assertIn(self.pet.rag_text, messages[-2]['content'])
        self.assertEqual(messages[-1]['content'], 'Hello')
        window._set_busy(True)
        self.assertIn('三叶', window._status.text())
        window._set_busy(False)
        self.assertTrue(window._status.isHidden())
        # Standalone configuration-error chat also uses the same persona.
        standalone = main.ChatWindow()
        self.assertEqual(standalone._build_chat_messages()[0]['content'], PERSONA)

    def test_balance_and_import_feedback_are_not_removed(self):
        self.pet._state = 'query'
        self.pet._on_balance_result(self.pet._query_seq, 'DeepSeek 余额：¥ 1.00')
        self.assertIsNotNone(self.pet._bubble)
        self.pet.exit_query()
        self.pet._enter_file_import(True)
        self.assertEqual(self.pet._state, 'file_import')
        self.assertIsNotNone(self.pet._bubble)


if __name__ == '__main__':
    unittest.main(verbosity=2)
