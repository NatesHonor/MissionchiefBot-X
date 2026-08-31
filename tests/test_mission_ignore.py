import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from core.mission_ignore import filter_ignored_mission_ids, load_mission_ignore_rules


class MissionIgnoreTests(unittest.TestCase):
    def test_ids_exact_names_and_fragments_are_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "mission_ignore_list.json").write_text(
                json.dumps(
                    {
                        "mission_ids": ["100"],
                        "mission_names": ["Bin fire"],
                        "contains": ["airport"]
                    }
                ),
                encoding="utf-8",
            )
            profile = SimpleNamespace(
                load_json=lambda filename, default: json.loads(
                    (path / filename).read_text(encoding="utf-8")
                )
            )
            rules = load_mission_ignore_rules(profile)
            remaining, ignored = filter_ignored_mission_ids(
                ["100", "101", "102"],
                rules,
                mission_index=[
                    {"id": "7", "name": "Bin fire"},
                    {"id": "8", "name": "Airport rescue"},
                ],
                marker_records={
                    "101": {"type_id": "7"},
                    "102": {"type_id": "8"},
                },
            )

        self.assertEqual(remaining, [])
        self.assertEqual([item[0] for item in ignored], ["100", "101", "102"])

    def test_simple_array_accepts_ids_and_exact_names(self):
        profile = SimpleNamespace(
            load_json=lambda filename, default: ["200", "Train station fire"]
        )
        rules = load_mission_ignore_rules(profile)
        remaining, ignored = filter_ignored_mission_ids(
            ["200", "201"],
            rules,
            cached_missions={"201": {"mission_name": "Train station fire"}},
        )

        self.assertEqual(remaining, [])
        self.assertEqual([item[0] for item in ignored], ["200", "201"])


if __name__ == "__main__":
    unittest.main()
