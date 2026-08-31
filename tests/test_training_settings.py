import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys

sys.modules.setdefault("art", SimpleNamespace())

from core.settings import load_settings
from utils.training import MAX_EMPLOYEES_PER_ROOM, _priority


class TrainingSettingsTests(unittest.TestCase):
    def test_training_plan_loads_school_course_and_room_capacity(self):
        config = """
[bot]
version = 3.0.2
region = ger
[credentials]
username = user
password = pass
[browser_settings]
headless = true
browsers = 2
browser_scaling = false
[missions]
dispatch = Default
dispatch_concurrent_missions = true
dispatch_incomplete_missions = false
dispatch_vehicles_by_distance = false
[other]
auto_training = true
auto_tasks = false
[delays]
dynamic_delays = false
dynamic_missions = false
dynamic_transport = false
missions = 30
other = 60
[trainings]
[trainings.fire_school]
school = Feuerwehrschule Nord
training = Atemschutz
rooms = 2
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text(config, encoding="utf-8")
            settings = load_settings(path)

        self.assertTrue(settings.auto_training)
        self.assertEqual(len(settings.training_plans), 1)
        self.assertEqual(settings.training_plans[0].school, "Feuerwehrschule Nord")
        self.assertEqual(settings.training_plans[0].course, "Atemschutz")
        self.assertEqual(settings.training_plans[0].rooms, 2)
        self.assertEqual(settings.dispatch_delay, 0)

    def test_untrained_staff_are_prioritized_before_completed_staff(self):
        self.assertLess(_priority("Nicht ausgebildet", "Atemschutz"), _priority("Ausgebildet", "Atemschutz"))
        self.assertEqual(MAX_EMPLOYEES_PER_ROOM, 10)


if __name__ == "__main__":
    unittest.main()
