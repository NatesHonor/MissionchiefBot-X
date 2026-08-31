import unittest
from types import SimpleNamespace

import sys

sys.modules.setdefault("art", SimpleNamespace())

from core.dispatching.vehicles import find_vehicle_ids
from core.regions import get_region_profile


class GermanRegionTests(unittest.TestCase):
    def test_german_region_is_wired_into_shared_runtime(self):
        profile = get_region_profile("ger")

        self.assertTrue(profile.runtime_supported)
        self.assertEqual(profile.language, "de")
        self.assertEqual(profile.base_url, "https://www.leitstellenspiel.de/")

    def test_german_vehicle_names_resolve_with_accents_and_variants(self):
        profile = get_region_profile("ger")
        state = SimpleNamespace(
            get_data=lambda: {
                "Löschfahrzeug (LF 20)": ["101"],
                "Hilfeleistungslöschfahrzeug": ["202"],
                "Streifenwagen": ["303"],
            },
            is_locked=lambda vehicle_id: False,
        )

        vehicle_ids = __import__("asyncio").run(
            find_vehicle_ids("löschfahrzeug", profile, state)
        )

        self.assertEqual(vehicle_ids, ["101", "202"])


if __name__ == "__main__":
    unittest.main()
