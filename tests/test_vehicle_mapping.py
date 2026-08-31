import importlib
import asyncio
import sys
import unittest
from types import SimpleNamespace

sys.modules.setdefault("art", SimpleNamespace())

from core.dispatching.vehicles import find_vehicle_ids
from core.regions import get_region_profile, supported_regions
from core.vehicle_mapping import vehicle_name_variants


class VehicleMappingTests(unittest.TestCase):
    def setUp(self):
        self.profile = get_region_profile("us")
        self.state = SimpleNamespace(
            get_data=lambda: {
                "Battalion chief unit": ["bc-1"],
                "Rescue Engine": ["rescue-1"],
                "SWAT Armoured Vehicle": ["swat-armoured-1"],
                "SWAT SUV": ["swat-suv-1"],
            },
            is_locked=lambda vehicle_id: False,
        )

    def test_mission_labels_resolve_after_parser_plural_normalization(self):
        battalion = asyncio.run(
            find_vehicle_ids("battalion chief vehicle", self.profile, self.state, quiet=True)
        )
        heavy_rescue = asyncio.run(
            find_vehicle_ids("heavy rescue vehicle", self.profile, self.state, quiet=True)
        )

        self.assertEqual(battalion, ["bc-1"])
        self.assertEqual(heavy_rescue, ["rescue-1"])

    def test_vehicle_unit_variants_are_limited_to_equivalent_labels(self):
        self.assertEqual(
            vehicle_name_variants("battalion chief vehicle")
            & vehicle_name_variants("Battalion chief unit"),
            {
                "battalion chief vehicle",
                "battalion chief vehicles",
                "battalion chief unit",
                "battalion chief units",
            },
        )
        armoured = asyncio.run(
            find_vehicle_ids(
                "SWAT Armoured Vehicle",
                self.profile,
                self.state,
                exact=True,
                quiet=True,
            )
        )
        self.assertEqual(armoured, ["swat-armoured-1"])

    def test_every_region_passes_the_mapping_audit(self):
        for region in supported_regions():
            with self.subTest(region=region):
                self.assertEqual(get_region_profile(region).validate_vehicle_mappings(), [])

    def test_every_declared_region_mapping_resolves_to_an_inventory_type(self):
        for region in supported_regions():
            profile = get_region_profile(region)
            module = importlib.import_module(profile.vehicle_options_module)
            requests = set(profile.vehicle_aliases())
            requests.update(module.VEHICLE_OPTIONS)
            for requested in requests:
                with self.subTest(region=region, requested=requested):
                    options = profile.vehicle_options(requested)
                    self.assertTrue(options)
                    state = SimpleNamespace(
                        get_data=lambda: {options[0]: [f"{region}-vehicle"]},
                        is_locked=lambda vehicle_id: False,
                    )
                    self.assertEqual(
                        asyncio.run(
                            find_vehicle_ids(requested, profile, state, quiet=True)
                        ),
                        [f"{region}-vehicle"],
                    )


if __name__ == "__main__":
    unittest.main()
