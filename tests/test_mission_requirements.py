import unittest

from core.mission_requirements import parse_requirement_count


class MissionRequirementCountTests(unittest.TestCase):
    def test_numeric_requirement_count_is_parsed(self):
        self.assertEqual(parse_requirement_count("2"), 2)
        self.assertEqual(parse_requirement_count(" 12 "), 12)

    def test_informational_count_is_ignored(self):
        self.assertIsNone(parse_requirement_count("yes"))
        self.assertIsNone(parse_requirement_count("when available"))

    def test_existing_cached_numeric_text_remains_dispatchable(self):
        self.assertEqual(parse_requirement_count("1"), 1)


if __name__ == "__main__":
    unittest.main()
