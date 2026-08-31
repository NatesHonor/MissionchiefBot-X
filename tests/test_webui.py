import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen

from core.webui import BotWebUI, save_settings


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
                self.assertIn(b"MissionchiefBot-X", response.read())
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


if __name__ == "__main__":
    unittest.main()
