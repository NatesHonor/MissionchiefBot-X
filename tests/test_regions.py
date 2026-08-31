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


class SwedishRegionTests(unittest.TestCase):
    def test_swedish_region_and_alias_are_wired_into_shared_runtime(self):
        profile = get_region_profile("se")

        self.assertEqual(profile.key, "swe")
        self.assertTrue(profile.runtime_supported)
        self.assertEqual(profile.language, "sv")
        self.assertEqual(profile.base_url, "https://www.larmcentralen-spelet.se/")

    def test_swedish_vehicle_names_resolve(self):
        profile = get_region_profile("swe")
        state = SimpleNamespace(
            get_data=lambda: {
                "BAS 1": ["401"],
                "släckbil": ["402"],
                "Radiobil": ["403"],
            },
            is_locked=lambda vehicle_id: False,
        )

        vehicle_ids = __import__("asyncio").run(
            find_vehicle_ids("firetruck", profile, state)
        )

        self.assertEqual(vehicle_ids, ["401", "402"])


class PortugueseRegionTests(unittest.TestCase):
    def test_portuguese_region_and_alias_are_wired_into_shared_runtime(self):
        profile = get_region_profile("portugal")

        self.assertEqual(profile.key, "pt")
        self.assertTrue(profile.runtime_supported)
        self.assertEqual(profile.language, "pt")
        self.assertEqual(profile.base_url, "https://www.jogo-operador112.com/")

    def test_portuguese_vehicle_names_resolve(self):
        profile = get_region_profile("pt")
        state = SimpleNamespace(
            get_data=lambda: {
                "VFCI": ["501"],
                "Veículo de Combate a Incêndios": ["502"],
                "Carro de Patrulha": ["503"],
            },
            is_locked=lambda vehicle_id: False,
        )

        vehicle_ids = __import__("asyncio").run(
            find_vehicle_ids("firetruck", profile, state)
        )

        self.assertEqual(vehicle_ids, ["501", "502"])


if __name__ == "__main__":
    unittest.main()
