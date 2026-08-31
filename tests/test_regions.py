import unittest
import importlib
from types import SimpleNamespace

import sys

sys.modules.setdefault("art", SimpleNamespace())

from core.dispatching.vehicles import find_vehicle_ids
from core.regions import get_region_profile, supported_regions


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


class FrenchRegionTests(unittest.TestCase):
    def test_french_region_and_alias_are_wired_into_shared_runtime(self):
        profile = get_region_profile("france")

        self.assertEqual(profile.key, "fr")
        self.assertTrue(profile.runtime_supported)
        self.assertEqual(profile.language, "fr")
        self.assertEqual(profile.base_url, "https://www.operateur112.fr/")

    def test_french_vehicle_names_resolve(self):
        profile = get_region_profile("fr")
        state = SimpleNamespace(
            get_data=lambda: {
                "FPT": ["701"],
                "Véhicule de Secours et d'Assistance aux Victimes": ["702"],
                "Véhicule de patrouille": ["703"],
            },
            is_locked=lambda vehicle_id: False,
        )

        vehicle_ids = __import__("asyncio").run(
            find_vehicle_ids("firetruck", profile, state)
        )

        self.assertEqual(vehicle_ids, ["701"])


class DanishRegionTests(unittest.TestCase):
    def test_danish_region_and_alias_are_wired_into_shared_runtime(self):
        profile = get_region_profile("danish")

        self.assertEqual(profile.key, "dk")
        self.assertTrue(profile.runtime_supported)
        self.assertEqual(profile.language, "da")
        self.assertEqual(profile.base_url, "https://www.alarmcentral-spil.dk/")

    def test_danish_vehicle_names_resolve(self):
        profile = get_region_profile("dk")
        state = SimpleNamespace(
            get_data=lambda: {
                "Brandbil": ["601"],
                "Stigevogn": ["602"],
                "Politibil": ["603"],
            },
            is_locked=lambda vehicle_id: False,
        )

        vehicle_ids = __import__("asyncio").run(
            find_vehicle_ids("firetruck", profile, state)
        )

        self.assertEqual(vehicle_ids, ["601"])


class RegionRegistryTests(unittest.TestCase):
    def test_every_registered_region_has_the_shared_runtime_contract(self):
        expected = {"us", "uk", "aus", "ger", "nld", "swe", "pt", "dk"}
        expected.add("pl")
        expected.add("fr")
        self.assertEqual(set(supported_regions()), expected)
        for region in expected:
            profile = get_region_profile(region)
            self.assertTrue(profile.runtime_supported)
            self.assertTrue(profile.base_url.endswith("/"))
            self.assertTrue(profile.vehicle_options("firetruck"))
            self.assertEqual(profile.validate_data_contract(), [])

    def test_every_registered_region_has_a_compatibility_entrypoint(self):
        for region in supported_regions():
            with self.subTest(region=region):
                profile = get_region_profile(region)
                module_name, function_name = profile.entrypoint.split(":")
                module = importlib.import_module(module_name)
                self.assertTrue(callable(getattr(module, function_name)))

    def test_region_aliases_resolve_to_canonical_profiles(self):
        self.assertEqual(get_region_profile("usa").key, "us")
        self.assertEqual(get_region_profile("australia").key, "aus")
        self.assertEqual(get_region_profile("nl").key, "nld")
        self.assertEqual(get_region_profile("de").key, "ger")
        self.assertEqual(get_region_profile("sv").key, "swe")

    def test_polish_region_accepts_its_official_hostname(self):
        profile = get_region_profile("https://www.operatorratunkowy.pl/")
        self.assertEqual(profile.key, "pl")
        self.assertEqual(profile.language, "pl")
        self.assertEqual(profile.base_url, "https://www.operatorratunkowy.pl/")

    def test_french_region_accepts_its_official_hostname(self):
        profile = get_region_profile("https://www.operateur112.fr/")
        self.assertEqual(profile.key, "fr")
        self.assertEqual(profile.language, "fr")
        self.assertEqual(profile.base_url, "https://www.operateur112.fr/")

    def test_region_urls_and_hosts_resolve_to_their_dedicated_profiles(self):
        self.assertEqual(get_region_profile("https://www.missionchief.co.uk/").key, "uk")
        self.assertEqual(get_region_profile("missionchief.co.uk").key, "uk")
        self.assertEqual(get_region_profile("https://www.leitstellenspiel.de").key, "ger")

    def test_unknown_region_is_not_silently_mapped_to_another_country(self):
        with self.assertRaisesRegex(ValueError, "no dedicated MissionChief adapter"):
            get_region_profile("new zealand")


if __name__ == "__main__":
    unittest.main()
