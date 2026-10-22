"""SQLite migration: shipped defaults persist, gathered data is never shipped."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys

sys.modules.setdefault("art", SimpleNamespace())

from core import data_store
import sqlite3

from core.region_defaults import (
    DEFAULT_DOCUMENTS,
    GATHERED_DOCUMENTS,
    PROJECT_ROOT,
    SEED_DATABASE,
    has_shipped_default,
    seed_region_defaults,
    shipped_default,
)
from core.regions import get_region_profile, supported_regions


class _TempDatabase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("MISSIONCHIEF_DB_PATH")
        os.environ["MISSIONCHIEF_DB_PATH"] = str(Path(self._tmp.name) / "test.sqlite3")

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("MISSIONCHIEF_DB_PATH", None)
        else:
            os.environ["MISSIONCHIEF_DB_PATH"] = self._previous
        self._tmp.cleanup()


class ShippedFilesTests(unittest.TestCase):
    def test_regions_are_single_modules_without_folders(self):
        for region in supported_regions():
            self.assertTrue((PROJECT_ROOT / "regions" / f"{region}.py").is_file(), region)
            self.assertFalse((PROJECT_ROOT / "regions" / region).exists(), region)

    def test_defaults_ship_in_one_seed_database_not_folders(self):
        self.assertTrue(SEED_DATABASE.is_file())
        self.assertFalse((PROJECT_ROOT / "regions" / "defaults").exists())

    def test_every_region_ships_every_default(self):
        for region in supported_regions():
            for filename in DEFAULT_DOCUMENTS:
                self.assertTrue(has_shipped_default(region, filename), f"{region}/{filename}")

    def test_gathered_data_is_never_shipped(self):
        connection = sqlite3.connect(f"file:{SEED_DATABASE.as_posix()}?mode=ro", uri=True)
        try:
            documents = {row[0] for row in connection.execute("SELECT DISTINCT document FROM defaults")}
        finally:
            connection.close()
        self.assertEqual(documents, set(DEFAULT_DOCUMENTS))
        self.assertFalse(documents & set(GATHERED_DOCUMENTS))


class SeedingTests(_TempDatabase):
    def test_defaults_are_seeded_into_the_database(self):
        profile = get_region_profile("us")
        written = seed_region_defaults(profile.key, profile.data_dir)
        self.assertEqual(sorted(written), sorted(DEFAULT_DOCUMENTS))
        stored = data_store.load_document(profile.vehicle_aliases_file, None)
        self.assertEqual(stored, shipped_default("us", "vehicle_aliases.json"))

    def test_seeding_twice_writes_nothing(self):
        profile = get_region_profile("us")
        seed_region_defaults(profile.key, profile.data_dir)
        self.assertEqual(seed_region_defaults(profile.key, profile.data_dir), [])

    def test_seeding_never_replaces_the_user_database_file(self):
        profile = get_region_profile("us")
        data_store.save_document(profile.vehicle_file, {"Patrol Car": ["1001"]})
        seed_region_defaults(profile.key, profile.data_dir)
        self.assertEqual(data_store.load_document(profile.vehicle_file, None), {"Patrol Car": ["1001"]})
        self.assertNotEqual(data_store.database_path().resolve(), SEED_DATABASE.resolve())

    def test_user_changes_survive_reseeding(self):
        profile = get_region_profile("us")
        seed_region_defaults(profile.key, profile.data_dir)
        custom = {"patrol car": ["My Custom Cruiser"]}
        profile.save_json("vehicle_aliases.json", custom)
        seed_region_defaults(profile.key, profile.data_dir)
        self.assertEqual(profile.vehicle_aliases(), custom)

    def test_defaults_load_without_explicit_seeding(self):
        profile = get_region_profile("uk")
        self.assertEqual(profile.requirement_mapping(), shipped_default("uk", "requirement_mapping.json"))


class GatheringTests(_TempDatabase):
    def test_gathered_documents_start_empty_so_the_bot_gathers_them(self):
        profile = get_region_profile("us")
        profile.ensure_data_dir()
        for path in (profile.vehicle_file, profile.building_file, profile.mission_file, profile.mission_index_file):
            self.assertFalse(data_store.document_has_records(path), path.name)

    def test_gathered_documents_count_once_stored(self):
        profile = get_region_profile("us")
        data_store.save_document(profile.vehicle_file, {"Patrol Car": ["1001"]})
        self.assertTrue(data_store.document_has_records(profile.vehicle_file))
        data_store.save_document(profile.building_file, {})
        self.assertFalse(data_store.document_has_records(profile.building_file))


if __name__ == "__main__":
    unittest.main()
