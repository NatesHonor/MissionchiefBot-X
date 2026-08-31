import sys
import unittest
from types import SimpleNamespace

sys.modules.setdefault("art", SimpleNamespace())

from core.missionchief_api import (
    extract_mission_ids,
    extract_mission_marker_records,
    mission_marker_endpoints,
    records_from_payload,
    vehicle_inventory_from_records,
)
from utils.transport import transport_option_key


class ApiAndTransportTests(unittest.TestCase):
    def test_vehicle_api_shapes_and_inventory_preserve_ids(self):
        payload = {
            "result": [
                {"id": 11, "caption": "01 Ambulance"},
                {"id": 12, "vehicle_type_caption": "HazMat", "caption": "02 HazMat"},
            ]
        }

        records = records_from_payload(payload)
        inventory = vehicle_inventory_from_records(records)

        self.assertEqual([record["id"] for record in records], [11, 12])
        self.assertEqual(inventory["01 Ambulance"], ["11"])
        self.assertEqual(inventory["HazMat"], ["12"])

    def test_marker_ids_are_deduplicated(self):
        markers = 'const mList = [{id: 42, mtid: 9}, {"mission_id": "43"}, {id: 42}]'

        self.assertEqual(extract_mission_ids(markers), ["42", "43"])

    def test_marker_records_keep_mission_type_ids_for_ignore_matching(self):
        markers = 'const mList = [{id: 42, mtid: 9}, {"mission_id": "43", "missionTypeId": 10}]'

        self.assertEqual(
            extract_mission_marker_records(markers),
            [
                {"id": "42", "type_id": "9", "name": None},
                {"id": "43", "type_id": "10", "name": None},
            ],
        )

    def test_mission_marker_feeds_can_be_limited_to_personal_missions(self):
        self.assertEqual(
            mission_marker_endpoints(False),
            ("/map/mission_markers_own.js.erb",),
        )
        self.assertEqual(
            mission_marker_endpoints(True),
            (
                "/map/mission_markers_own.js.erb",
                "/map/mission_markers_alliance.js.erb",
            ),
        )

    def test_transport_priority_is_department_ownership_tax_then_distance(self):
        best = {
            "has_department": True,
            "own": True,
            "tax": 50,
            "distance": 30,
        }
        closer_but_wrong_department = {
            "has_department": False,
            "own": True,
            "tax": 0,
            "distance": 1,
        }

        self.assertLess(transport_option_key(best), transport_option_key(closer_but_wrong_department))


if __name__ == "__main__":
    unittest.main()
