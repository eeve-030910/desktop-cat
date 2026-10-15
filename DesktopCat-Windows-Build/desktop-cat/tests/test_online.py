import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import online_content as content
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
from update_ui import UpdateMonitor
from desktop_sparrow import DesktopCat, CharacterWindow

HOSTS = ["download.example"]
POLICY = {"schema":1, "minimum_version":"0.4.0", "latest_version":"0.4.1",
          "download_url":"https://download.example/setup",
          "catalog_url":"https://download.example/catalog.json"}


class OnlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def test_minimum_and_optional_update(self):
        self.assertTrue(content.check_policy(POLICY, HOSTS, "0.4.0"))
        self.assertFalse(content.check_policy(POLICY, HOSTS, "0.3.3"))
        self.assertTrue(content.check_policy(POLICY, HOSTS, "0.4.1"))

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            content.check_policy({**POLICY, "minimum_version":"9.0.0"}, HOSTS)
        with self.assertRaises(ValueError):
            content.version("0.4")

    def test_unconfigured_blocks(self):
        with self.assertRaises(ValueError):
            content.load_policy({"policy_url":"", "allowed_hosts":[]})

    def test_development_skips_network_and_runs_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("update_ui.BUILD_CHANNEL", "development"), patch("update_ui.load_policy") as remote:
                monitor = UpdateMonitor(self.app, Path(directory)/"missing.json")
                permitted = []
                monitor.permitted.connect(lambda: permitted.append(True))
                monitor.check()
                self.assertTrue(monitor.allowed)
                self.assertTrue(permitted)
                self.assertFalse(monitor.periodic.isActive())
                remote.assert_not_called()
                self.assertIsNone(monitor.worker)
                monitor.dialog.hide()

    def test_release_keeps_gate_and_periodic_check(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("update_ui.BUILD_CHANNEL", "release"):
                monitor = UpdateMonitor(self.app, Path(directory)/"missing.json")
                self.assertFalse(monitor.allowed)
                self.assertTrue(monitor.periodic.isActive())
                monitor.fail("未設定")
                self.assertFalse(monitor.allowed)
                self.assertTrue(monitor.dialog.isVisible())
                monitor.periodic.stop()
                monitor.dialog.hide()

    def test_untrusted_download_and_redirect(self):
        for url in ("http://download.example/a", "https://evil.example/a",
                    "file:///tmp/a", "https://user:password@download.example/a"):
            with self.assertRaises(ValueError):
                content.allowed_url(url, HOSTS)
        redirect = content.TrustedRedirects(HOSTS)
        with self.assertRaises(ValueError):
            redirect.redirect_request(None,None,302,"",{}, "https://evil.example/a")

    def make_package(self, extra=None):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            source = Path(__file__).resolve().parents[1] / "assets"
            for name in content.FILES:
                archive.write(source/name, name)
            if extra:
                archive.writestr(extra, b"malicious")
        raw = buffer.getvalue()
        item = {"id":"test_cat", "name":"テストねこ", "free":True,
                "minimum_app_version":"0.4.0", "url":"https://download.example/cat.zip",
                "sha256":hashlib.sha256(raw).hexdigest()}
        return item, raw

    def test_free_catalog_and_paid_exclusion(self):
        item, raw = self.make_package()
        entries = content.catalog_entries({"schema":1,"characters":[item]}, HOSTS)
        self.assertEqual(entries[0]["id"], "test_cat")
        with self.assertRaises(ValueError):
            content.catalog_entries({"schema":1,"characters":[{**item,"free":False}]}, HOSTS)

    def test_install_data_only(self):
        item, raw = self.make_package()
        with tempfile.TemporaryDirectory() as directory:
            result = content.install_character(item, raw, directory)
            self.assertTrue((result/"cat_sleep.png").is_file())
            self.assertEqual(content.install_character(item, raw, directory), result)
            with self.assertRaises(ValueError):
                content.install_character(item, raw+b"tampered", directory)

    def test_reject_archive_path_and_executable(self):
        for extra in ("../outside.png", "run.exe"):
            item, raw = self.make_package(extra)
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    content.install_character(item, raw, directory)

    def test_existing_care_and_update_block(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory)/"test.ini"), QSettings.IniFormat)
            pet = DesktopCat(self.app)
            pet.timer.stop()
            window = CharacterWindow(pet, settings)
            monitor = UpdateMonitor(self.app, Path(directory)/"missing.json")
            self.app.updates = monitor
            self.app.selector = window
            window.feed_button.click()
            self.assertGreater(pet.heart_until, pet.heart_start)
            pet.fall_asleep()
            self.assertTrue(pet.sleeping)
            pet.feed()
            self.assertFalse(pet.sleeping)
            blocked = []
            monitor.blocked.connect(lambda: blocked.append(True))
            monitor.accept_policy(({**POLICY,"minimum_version":"0.4.1"}, False))
            self.assertTrue(blocked)
            pet.policy_allowed = False
            pet.hide()
            window.setEnabled(False)
            pet.feed()
            self.assertFalse(pet.isVisible())
            window.toggle_pet()
            self.assertFalse(pet.isVisible())
            monitor.dialog.hide()
            monitor.periodic.stop()
            window.close()


if __name__ == "__main__":
    unittest.main()
