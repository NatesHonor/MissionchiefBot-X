import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen

from core.settings import load_settings
from core.webui import BotWebUI, read_log_tail, save_settings


class WebUITests(unittest.TestCase):
    def _settings(self):
        values = {name: False for name in (
            "headless",
            "browser_scaling",
            "dispatch_by_distance",
            "dispatch_incomplete",
            "dynamic_missions",
            "include_alliance_missions",
            "concurrent_missions",
            "auto_training",
            "auto_recruiting",
            "auto_special_resources",
            "auto_tasks",
            "dynamic_delays",
            "dynamic_delay_missions",
            "dynamic_delay_transport",
        )}
        values.update(
            region="us",
            browsers=2,
            dispatch_type="Default",
            max_missions=500,
            mission_delay=30,
            other_delay=60,
            dispatch_delay=0,
            username="hidden-user",
            password="hidden-password",
        )
        return SimpleNamespace(**values)

    def test_local_server_exposes_status_without_credentials(self):
        ui = BotWebUI(port=0)
        ui.set_settings(self._settings())
        ui.update(status="running", message="Monitoring", running=True, version="3.1.0")
        self.assertTrue(ui.start())
        try:
            with urlopen(f"{ui.url}/api/status", timeout=2) as response:
                payload = json.load(response)
            self.assertEqual(payload["status"], "running")
            self.assertEqual(payload["version"], "3.1.0")
            self.assertNotIn("hidden-password", json.dumps(payload))
            with urlopen(f"{ui.url}/", timeout=2) as response:
                page = response.read()
            self.assertIn(b"MissionchiefBot-X", page)
            self.assertIn(b"Start bot", page)
            self.assertNotIn(b"Unavailable", page)
            self.assertNotIn(b'class="mark"', page)
        finally:
            ui.stop()

    def test_control_callbacks_are_called(self):
        ui = BotWebUI(port=0)
        events = []
        ui.set_control_callbacks(start=lambda: events.append("start"), stop=lambda: events.append("stop"))
        self.assertTrue(ui.start())
        try:
            for action in ("start", "stop"):
                request = Request(
                    f"{ui.url}/api/control",
                    data=json.dumps({"action": action}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=2) as response:
                    self.assertEqual(json.load(response)["accepted"], True)
            self.assertEqual(events, ["start", "stop"])
        finally:
            ui.stop()

    def test_settings_are_validated_and_written(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text("[bot]\nregion = us\n", encoding="utf-8")
            saved = save_settings({"region": "UK", "mission_delay": 15}, path)
            self.assertEqual(saved["region"], "uk")
            contents = path.read_text(encoding="utf-8")
            self.assertIn("region = uk", contents)
            self.assertIn("missions = 15", contents)
            with self.assertRaises(ValueError):
                save_settings({"password": "must-not-be-editable"}, path)

    def test_webui_configuration_is_loaded(self):
        example = Path(__file__).parents[1] / "config.ini.example"
        contents = example.read_text(encoding="utf-8").replace("username =", "username = test-user")
        contents = contents.replace("password =", "password = test-password")
        contents = contents.replace("enabled = false", "enabled = true")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text(contents, encoding="utf-8")
            settings = load_settings(path)
        self.assertTrue(settings.webui_enabled)
        self.assertEqual(settings.webui_host, "127.0.0.1")
        self.assertEqual(settings.webui_port, 8765)

    def test_log_tail_excludes_webui_access_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missionchiefbot.log"
            path.write_text(
                "2026 INFO Starting mission logic.\n"
                "2026 INFO WebUI 127.0.0.1 - GET /api/status\n"
                "2026 INFO Dispatched mission 123\n",
                encoding="utf-8",
            )
            previous = os.environ.get("MISSIONCHIEF_LOG_FILE")
            os.environ["MISSIONCHIEF_LOG_FILE"] = str(path)
            try:
                self.assertEqual(
                    read_log_tail(),
                    ["2026 INFO Starting mission logic.", "2026 INFO Dispatched mission 123"],
                )
            finally:
                if previous is None:
                    os.environ.pop("MISSIONCHIEF_LOG_FILE", None)
                else:
                    os.environ["MISSIONCHIEF_LOG_FILE"] = previous


if __name__ == "__main__":
    unittest.main()
