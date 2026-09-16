import asyncio
import sys
import unittest
from types import SimpleNamespace

# Keep this resolver test runnable in a minimal checkout without installing
# the optional console-art dependency used by the runtime logger.
sys.modules.setdefault("art", SimpleNamespace())

from core.dispatching.vehicles import find_vehicle_ids
from utils.vehicle_options import get_vehicle_options


class WreckerDispatchTests(unittest.TestCase):
    def test_wrecker_alias_includes_specialized_wreckers(self):
        self.assertEqual(
            get_vehicle_options("wrecker"),
            ["Wrecker", "Police Wrecker", "Fire Wrecker"],
        )

    def test_wrecker_lookup_resolves_police_and_fire_inventory(self):
        profile = SimpleNamespace(vehicle_options=get_vehicle_options)
        state = SimpleNamespace(
            get_data=lambda: {
                "Police Wrecker": ["101"],
                "Fire Wrecker": ["202"],
                "Ambulance": ["303"],
            },
            is_locked=lambda vehicle_id: False,
        )

        vehicle_ids = asyncio.run(find_vehicle_ids("wrecker", profile, state))

        self.assertEqual(vehicle_ids, ["101", "202"])


if __name__ == "__main__":
    unittest.main()
