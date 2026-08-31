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
from core.mission_collector import limit_mission_ids
from utils.transport import (
    choose_transport_option,
    is_patient_transport_option,
    is_transport_request,
    transport_option_key,
)


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
        self.assertEqual(inventory["Ambulance"], ["11"])
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

    def test_large_mission_feeds_are_bounded_without_dropping_active_cache_state(self):
        ids, omitted = limit_mission_ids(["1", "2", "3"], 2)
        self.assertEqual(ids, ["1", "2"])
        self.assertEqual(omitted, 1)
        self.assertEqual(limit_mission_ids(["1", "2"], 0), (["1", "2"], 0))
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

    def test_transport_request_accepts_api_flag_variants(self):
        self.assertTrue(is_transport_request({"fms_real": 5}))
        self.assertTrue(is_transport_request({"transportType": "patient_transport"}))
        self.assertTrue(is_transport_request({"transport_requested": True}))
        self.assertTrue(is_transport_request({"needs_transport": "yes"}))
        self.assertFalse(is_transport_request({"fms_real": 1}))

    def test_patient_transport_prefers_explicit_hospital_action(self):
        patient = {
            "action_label": "Transport Patient",
            "has_department": False,
            "own": False,
            "tax": 0,
            "distance": 20,
        }
        unrelated = {
            "action_label": "Visit hospital",
            "has_department": True,
            "own": True,
            "tax": 0,
            "distance": 1,
        }

        self.assertTrue(is_patient_transport_option(patient))
        self.assertIs(choose_transport_option([unrelated, patient])["action_label"], "Transport Patient")


if __name__ == "__main__":
    unittest.main()
