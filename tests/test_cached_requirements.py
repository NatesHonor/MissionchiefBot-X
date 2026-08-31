import sys
import unittest
from types import SimpleNamespace

sys.modules.setdefault("art", SimpleNamespace())

from core.mission_requirements import normalize_cached_requirements
from core.mission_requirements import resolve_personnel
from core.regions import get_region_profile


class CachedRequirementMigrationTests(unittest.TestCase):
    def test_swat_vehicle_variant_resolves_to_personnel(self):
        self.assertEqual(
            resolve_personnel("SWAT personnel in SWAT vehicles", get_region_profile("us")),
            "swat personnel",
        )

    def test_old_cached_swat_requirement_is_migrated_before_dispatch(self):
        data = {
            "vehicles": [
                {"options": ["swat personnel in swat vehicles"], "count": 18},
                {"options": ["patrol car", "SWAT Armoured Vehicle"], "count": 1},
            ],
            "personnel": [],
        }

        normalize_cached_requirements(data, get_region_profile("us"))

        self.assertEqual(len(data["vehicles"]), 1)
        self.assertEqual(
            data["vehicles"][0]["options"],
            ["patrol car", "SWAT Armoured Vehicle"],
        )
        self.assertEqual(data["personnel"], [{"name": "swat personnel", "count": 18}])


if __name__ == "__main__":
    unittest.main()
