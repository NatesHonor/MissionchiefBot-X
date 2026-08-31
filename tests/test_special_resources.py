import unittest

from utils.special_resources import is_special_resource_control


class SpecialResourceControlTests(unittest.TestCase):
    def test_recognizes_named_event_resources(self):
        self.assertTrue(is_special_resource_control("button collect_special_resource snowman"))
        self.assertTrue(is_special_resource_control("img /images/events/pumpkin.png"))

    def test_ignores_mission_links_and_requirement_text(self):
        self.assertFalse(is_special_resource_control("a href=/missions/123"))
        self.assertFalse(is_special_resource_control("mission resource requirements"))


if __name__ == "__main__":
    unittest.main()
