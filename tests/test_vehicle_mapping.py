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

    def test_cross_role_fire_vehicle_mappings_include_quint_and_rescue_engine(self):
        for region in ("us", "uk", "aus"):
            with self.subTest(region=region):
                profile = get_region_profile(region)
                state = SimpleNamespace(
                    get_data=lambda: {
                        "Quint": [f"{region}-quint"],
                        "Rescue Engine": [f"{region}-rescue-engine"],
                    },
                    is_locked=lambda vehicle_id: False,
                )

                firetruck_ids = asyncio.run(
                    find_vehicle_ids("firetruck", profile, state, quiet=True)
                )
                platform_ids = asyncio.run(
                    find_vehicle_ids("platform truck", profile, state, quiet=True)
                )
                heavy_rescue_ids = asyncio.run(
                    find_vehicle_ids("heavy rescue vehicle", profile, state, quiet=True)
                )

                self.assertIn(f"{region}-quint", firetruck_ids)
                self.assertIn(f"{region}-quint", platform_ids)
                self.assertIn(f"{region}-rescue-engine", firetruck_ids)
                self.assertIn(f"{region}-rescue-engine", heavy_rescue_ids)

    def test_specific_us_vehicle_requirements_resolve_to_inventory_labels(self):
        profile = get_region_profile("us")
        state = SimpleNamespace(
            get_data=lambda: {
                "Patrol Boat": ["boat-1"],
                "Large Coastal Boat": ["boat-2"],
                "Quint": ["quint-1"],
                "Type 5 engine": ["wildland-1"],
                "Smoke Jumper Vehicle": ["smoke-1"],
            },
            is_locked=lambda vehicle_id: False,
        )

        self.assertEqual(
            asyncio.run(find_vehicle_ids("patrol boat", profile, state, quiet=True)),
            ["boat-1"],
        )
        self.assertEqual(
            asyncio.run(find_vehicle_ids("large rescue boat", profile, state, quiet=True)),
            ["boat-2"],
        )
        self.assertEqual(
            asyncio.run(find_vehicle_ids("platform", profile, state, quiet=True)),
            ["quint-1"],
        )
        self.assertEqual(
            asyncio.run(find_vehicle_ids("wildland trucks", profile, state, quiet=True)),
            ["wildland-1"],
        )
        self.assertEqual(
            asyncio.run(find_vehicle_ids("smoke jumpers", profile, state, quiet=True)),
            ["smoke-1"],
        )

    def test_aircraft_requirement_variants_dispatch_regional_air_vehicles(self):
        profile = get_region_profile("us")
        state = SimpleNamespace(
            get_data=lambda: {"Mobile air": ["air-1"]},
            is_locked=lambda vehicle_id: False,
        )

        self.assertEqual(
            asyncio.run(find_vehicle_ids("plane", profile, state, quiet=True)),
            ["air-1"],
        )
        self.assertEqual(
            asyncio.run(find_vehicle_ids("aircraft", profile, state, quiet=True)),
            ["air-1"],
        )

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
