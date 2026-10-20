import unittest

from core.dispatching.dispatcher import _merge_vehicle_requirements
from core.regions import get_region_profile


class DispatchExpansionTests(unittest.TestCase):
    def test_live_expansion_increases_cached_requirement_without_duplicates(self):
        requirements = [{"options": ["firetruck"], "count": 1}]

        _merge_vehicle_requirements(
            requirements,
            [{"name": "firetruck", "count": 3}],
            get_region_profile("us"),
        )

        self.assertEqual(requirements, [{"options": ["firetruck"], "count": 3}])

    def test_live_expansion_adds_new_requirement(self):
        requirements = [{"options": ["firetruck"], "count": 1}]

        _merge_vehicle_requirements(
            requirements,
            [{"name": "platform truck", "count": 1}],
            get_region_profile("us"),
        )

        self.assertEqual(len(requirements), 2)
        self.assertEqual(requirements[1]["count"], 1)


if __name__ == "__main__":
    unittest.main()
