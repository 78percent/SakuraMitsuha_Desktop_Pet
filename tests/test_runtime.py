"""Local-only checks. These never call DeepSeek or read a real key."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "CetaPet"))
import runtime_config
from PySide6.QtCore import QByteArray, QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtNetwork import QNetworkProxy, QNetworkReply
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
with tempfile.TemporaryDirectory() as import_config:
    with patch.object(runtime_config, "ENV_PATH", Path(import_config) / ".env"):
        import main as pet


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / ".env"
        self.config_patch = patch.object(runtime_config, "ENV_PATH", self.path)
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.temp.cleanup()

    def test_missing_blank_and_quoted_values(self):
        self.assertEqual(runtime_config.read_api_key(), "")
        self.path.write_text("DEEPSEEK_API_KEY=\n", encoding="utf-8")
        self.assertEqual(runtime_config.read_api_key(), "")
        self.path.write_text("DEEPSEEK_API_KEY='local-test-value'\n", encoding="utf-8-sig")
        self.assertEqual(runtime_config.read_api_key(), "local-test-value")

    def test_save_preserves_model_comments_and_does_not_interpolate(self):
        self.path.write_text("# keep comment\nDEEPSEEK_MODEL=chosen-model\nOTHER=keep\n", encoding="utf-8")
        runtime_config.save_api_key("unit-test-${DO_NOT_EXPAND}")
        self.assertEqual(runtime_config.read_api_key(), "unit-test-${DO_NOT_EXPAND}")
        self.assertEqual(runtime_config.read_model(), "chosen-model")
        self.assertIn("OTHER=keep", self.path.read_text(encoding="utf-8"))
        self.assertIn("# keep comment", self.path.read_text(encoding="utf-8"))

    def test_invalid_key_does_not_overwrite(self):
        runtime_config.save_api_key("local-existing")
        for value in ("", "a\nb", "a\rb", "a\0b"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    runtime_config.save_api_key(value)
                self.assertEqual(runtime_config.read_api_key(), "local-existing")


class FakeReply:
    def __init__(self, payload, status=200, error=QNetworkReply.NoError):
        self.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.status = status
        self.network_error = error

    def deleteLater(self):
        pass

    def readAll(self):
        return QByteArray(self.body)

    def attribute(self, unused):
        return self.status

    def error(self):
        return self.network_error

    def errorString(self):
        return "local simulated transport error"


@unittest.skipUnless(sys.platform == "win32", "Windows entry point")
class EntrypointTests(unittest.TestCase):
    def test_start_cmd_from_root_and_other_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            temp = Path(folder)
            # Inject a temporary configuration before the real launcher imports it.
            # The real .env is never read or modified, even if already configured.
            (temp / "sitecustomize.py").write_text(
                "import sys\nfrom pathlib import Path\n"
                f"sys.path.insert(0, {str(ROOT / 'CetaPet')!r})\n"
                "import runtime_config\n"
                f"runtime_config.ENV_PATH = Path({str(temp / '.env')!r})\n"
                "import single_instance\n"
                "original_instance = single_instance.SingleInstance\n"
                "def isolated_instance(root, parent=None, **kw):\n"
                f"    return original_instance(Path({str(temp)!r}), parent, **kw)\n"
                "single_instance.SingleInstance = isolated_instance\n"
                "from PySide6.QtWidgets import QDialog\n"
                "from PySide6.QtCore import QTimer\n"
                "original_exec = QDialog.exec\n"
                "def cancel(self):\n"
                "    print('KEY_SETUP_CANCELLED', flush=True)\n"
                "    QTimer.singleShot(20, self.reject)\n"
                "    return original_exec(self)\n"
                "QDialog.exec = cancel\n", encoding="utf-8")
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(temp)
            for directory, options in ((ROOT,[]), (temp,[]), (temp,["--legacy"])):
                child = subprocess.run(["cmd", "/d", "/c", str(ROOT / "start_pet.cmd"), *options],
                                       cwd=directory, env=environment, capture_output=True,
                                       encoding="utf-8", errors="replace", timeout=20)
                self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
                self.assertIn("KEY_SETUP_CANCELLED", child.stdout)
                self.assertIn("TLS backend: schannel", child.stdout)
                self.assertFalse((temp / ".env").exists())


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config_patch = patch.object(runtime_config, "ENV_PATH", Path(self.temp.name) / ".env")
        self.config_patch.start()
        self.key_patch = patch.object(pet, "_CURRENT_KEY", "")
        self.key_patch.start()
        self.rag_patch = patch.object(pet, "RAG_DIR", str(Path(self.temp.name) / "RAG"))
        self.rag_patch.start()
        self.position_patch = patch.object(pet, "CONFIG_PATH", str(Path(self.temp.name) / "config.json"))
        self.position_patch.start()

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            widget.hide()
            widget.deleteLater()
        self.app.processEvents()
        self.position_patch.stop()
        self.rag_patch.stop()
        self.key_patch.stop()
        self.config_patch.stop()
        self.temp.cleanup()

    def test_empty_key_dialog_is_masked_cancel_does_not_write(self):
        dialog = pet.ApiKeySetupDialog()
        self.assertEqual(dialog._edit.echoMode(), QLineEdit.Password)
        def cancel_dialog():
            for widget in self.app.topLevelWidgets():
                if isinstance(widget, pet.ApiKeySetupDialog):
                    widget.reject()
        QTimer.singleShot(10, cancel_dialog)
        self.assertFalse(pet.ensure_api_key_at_startup())
        self.assertFalse(runtime_config.ENV_PATH.exists())

    def test_dotenv_key_skips_input_dialog(self):
        runtime_config.save_api_key("local-test-key")
        with patch.object(pet, "ApiKeySetupDialog", side_effect=AssertionError("unexpected prompt")):
            self.assertTrue(pet.ensure_api_key_at_startup())
        self.assertEqual(pet.read_api_key(), "local-test-key")

    def test_change_dialog_preserves_settings_and_rejects_failed_key(self):
        runtime_config.ENV_PATH.write_text("DEEPSEEK_MODEL=chosen-model\n", encoding="utf-8")
        runtime_config.save_api_key("local-existing")
        dialog = pet.ChangeApiKeyDialog()
        self.assertEqual(dialog._edit.echoMode(), QLineEdit.Password)
        dialog._edit.setText("local-replacement")
        with patch.object(pet, "run_connectivity_test_blocking", return_value=False), \
                patch.object(pet, "open_chat_for_key_error"):
            dialog._on_confirm()
        self.assertEqual(runtime_config.read_api_key(), "local-existing")
        self.assertFalse(dialog._busy)
        with patch.object(pet, "run_connectivity_test_blocking", return_value=True):
            dialog._on_confirm()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(runtime_config.read_api_key(), "local-replacement")
        self.assertEqual(runtime_config.read_model(), "chosen-model")
        self.assertEqual(pet.read_api_key(), "local-replacement")

    def test_success_and_bad_responses_release_chat_controls(self):
        cases = [
            ({"choices": [{"message": {"content": "local simulated reply"}}]}, 200, QNetworkReply.NoError, True),
            ({"choices": [{"message": {"content": " "}}]}, 200, QNetworkReply.NoError, False),
            ({"choices": [{"message": {"content": 42}}]}, 200, QNetworkReply.NoError, False),
            ([], 200, QNetworkReply.NoError, False),
            (b"not-json", 200, QNetworkReply.NoError, False),
            ({"error": "unexpected-shape"}, 401, QNetworkReply.AuthenticationRequiredError, False),
            ({"error": {"message": "invalid local-secret"}}, 401, QNetworkReply.AuthenticationRequiredError, False),
            ({"error": {"message": "server unavailable"}}, 503, QNetworkReply.ServiceUnavailableError, False),
            ({}, None, QNetworkReply.TimeoutError, False),
            ({}, None, QNetworkReply.ConnectionRefusedError, False),
        ]
        with patch.object(pet, "_CURRENT_KEY", "local-secret"):
            for payload, status, error, success in cases:
                with self.subTest(status=status, error=error, payload_type=type(payload).__name__):
                    window = pet.ChatWindow()
                    window._set_busy(True)
                    window._reply = FakeReply(payload, status, error)
                    window._on_reply_finished()
                    self.assertFalse(window._busy)
                    self.assertTrue(window._edit.isEnabled())
                    self.assertEqual(len(window._history), int(success))
                    # Visible errors must never echo a supplied secret.
                    view = next(w for w in window.findChildren(pet.QTextEdit) if w is not window._edit)
                    self.assertNotIn("local-secret", view.toPlainText())
                    window.hide()
                    window.deleteLater()

    def test_actual_qt_http_request_and_retry_against_local_server(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                status = 401 if len(received) == 1 else 200
                data = {"error": {"message": "local deliberate failure"}} if status == 401 else {
                    "choices": [{"message": {"content": "local transport reply"}}]}
                body = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            address = f"http://127.0.0.1:{server.server_port}/chat/completions"
            with patch.object(pet, "CHAT_API_URL", address), patch.object(pet, "_CURRENT_KEY", "local-test"):
                window = pet.ChatWindow()
                window._nam.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
                for question in ("first local attempt", "local retry"):
                    window._edit.setText(question)
                    window._on_send()
                    for _ in range(100):
                        if not window._busy:
                            break
                        QTest.qWait(30)
                    self.assertFalse(window._busy)
                self.assertEqual(len(received), 2)
                self.assertEqual(received[1]["messages"][-1]["content"], "local retry")
                self.assertEqual(received[1]["thinking"], {"type": "disabled"})
                self.assertIn("local transport reply", window._view.toPlainText())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_asset_decode_and_click_drag_state(self):
        widget = pet.DesktopPet()
        for key in pet.IMAGE_RELS:
            pixmap = widget._load_state_pixmap(key)
            self.assertFalse(pixmap.isNull(), key)
        widget.show()
        widget.play_entrance()
        QTest.qWait(pet.CHEERUP_MS + 100)
        self.assertEqual(widget._state, "idle")
        QTest.mouseClick(widget, Qt.LeftButton)
        QTest.qWait(QApplication.doubleClickInterval() + 100)
        self.assertEqual(widget._state, "touch")
        QTest.qWait(pet.TOUCH_MS + 100)
        self.assertEqual(widget._state, "idle")
        old_pos = widget.pos()
        point = QPoint(30, 30)
        QTest.mousePress(widget, Qt.LeftButton, pos=point)
        target = widget.mapToGlobal(point) + QPoint(50, 20)
        move = QMouseEvent(QEvent.MouseMove, QPointF(widget.mapFromGlobal(target)),
                           QPointF(target), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        self.app.sendEvent(widget, move)
        self.assertEqual(widget._state, "pickup")
        self.assertNotEqual(widget.pos(), old_pos)
        QTest.mouseRelease(widget, Qt.LeftButton, pos=point)
        self.assertEqual(widget._state, "idle")
        self.assertFalse(widget._click_timer.isActive())
        menu = widget._build_context_menu()
        chat = next(action for action in menu.actions() if action.text() == "聊天")
        chat.trigger()
        self.assertTrue(widget._chat_window.isVisible())
        widget.hide_whale()
        self.assertTrue(widget.isHidden())
        widget.show_whale(greet=False)
        self.assertTrue(widget.isVisible())
        widget._cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
