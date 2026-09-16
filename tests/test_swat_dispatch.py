import asyncio
import sys
import unittest
from types import SimpleNamespace

sys.modules.setdefault("art", SimpleNamespace())

from core.dispatching.personnel import plan_personnel_vehicles
from core.dispatching.vehicles import find_vehicle_ids


class SwatDispatchTests(unittest.TestCase):
    def setUp(self):
        self.profile = SimpleNamespace(
            vehicle_options=lambda name: [],
            vehicle_aliases=lambda: {},
        )
        self.state = SimpleNamespace(
            get_data=lambda: {
                "SWAT Armoured Vehicle": ["101", "102"],
                "SWAT SUV": ["201", "202", "203"],
            },
            is_locked=lambda vehicle_id: False,
        )

    def test_exact_lookup_does_not_mix_swat_capacities(self):
        armoured = asyncio.run(
            find_vehicle_ids(
                "SWAT Armoured Vehicle",
                self.profile,
                self.state,
                exact=True,
                quiet=True,
            )
        )
        self.assertEqual(armoured, ["101", "102"])

    def test_personnel_plan_uses_capacity_not_a_shared_vehicle_alias(self):
        candidates = [
            ("SWAT Armoured Vehicle", 6, 2),
            ("SWAT SUV", 4, 3),
        ]

        self.assertEqual(
            plan_personnel_vehicles(6, candidates),
            [("SWAT Armoured Vehicle", 1)],
        )
        self.assertEqual(
            plan_personnel_vehicles(4, candidates),
            [("SWAT SUV", 1)],
        )
        self.assertEqual(
            plan_personnel_vehicles(10, candidates),
            [("SWAT Armoured Vehicle", 1), ("SWAT SUV", 1)],
        )


if __name__ == "__main__":
    unittest.main()
