import unittest
import asyncio

from core.mission_requirements import (
    gather_requirements,
    parse_requirement_count,
)
from core.regions import get_region_profile


class FakeElement:
    def __init__(self, text=""):
        self.text = text

    async def text_content(self):
        return self.text

    async def inner_text(self):
        return self.text


class FakeRequirementRow:
    async def inner_text(self):
        return "Required SWAT personnel in SWAT vehicles 6"

    async def query_selector(self, selector):
        if selector == "td:first-child":
            return FakeElement("SWAT personnel in SWAT vehicles")
        if selector == "td:nth-child(2)":
            return FakeElement("6")
        return None


class FakeRequirementTable:
    async def query_selector_all(self, selector):
        if selector == "tr:has(td)":
            return [FakeRequirementRow()]
        return []


class FakeMissionPage:
    def __init__(self):
        self.table = FakeRequirementTable()

    async def query_selector(self, selector):
        if "Vehicle and Personnel Requirements" in selector:
            return self.table
        return None

    async def query_selector_all(self, selector):
        return []


class MissionRequirementCountTests(unittest.TestCase):
    def test_numeric_requirement_count_is_parsed(self):
        self.assertEqual(parse_requirement_count("2"), 2)
        self.assertEqual(parse_requirement_count(" 12 "), 12)

    def test_informational_count_is_ignored(self):
        self.assertIsNone(parse_requirement_count("yes"))
        self.assertIsNone(parse_requirement_count("when available"))

    def test_existing_cached_numeric_text_remains_dispatchable(self):
        self.assertEqual(parse_requirement_count("1"), 1)

    def test_swat_vehicle_personnel_requirement_becomes_personnel(self):
        result = asyncio.run(gather_requirements(FakeMissionPage(), get_region_profile("us")))

        self.assertEqual(result["vehicles"], [])
        self.assertEqual(
            result["personnel"],
            [{"name": "swat personnel", "count": 6}],
        )


if __name__ == "__main__":
    unittest.main()
