import math
import unittest

from core.dispatching.vehicles import parse_distance_value


class DispatchDistanceTests(unittest.TestCase):
    def test_duration_text_is_converted_to_total_seconds(self):
        self.assertEqual(parse_distance_value("1 min 20 sec"), 80)
        self.assertEqual(parse_distance_value("0:53"), 53)

    def test_duration_sorting_does_not_treat_minutes_as_seconds(self):
        self.assertGreater(parse_distance_value("1 min 20 sec"), parse_distance_value("21 sec"))

    def test_missing_distance_is_sorted_last(self):
        self.assertTrue(math.isinf(parse_distance_value(None)))


if __name__ == "__main__":
    unittest.main()
