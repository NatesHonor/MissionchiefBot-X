import unittest
from types import SimpleNamespace

import sys

sys.modules.setdefault("art", SimpleNamespace())

from utils.recruiting import desired_recruitment_target


class RecruitingTests(unittest.TestCase):
    def test_recruiting_days_extend_current_staff_target(self):
        self.assertEqual(desired_recruitment_target(10, 10, 3), 13)

    def test_existing_higher_target_is_preserved(self):
        self.assertEqual(desired_recruitment_target(10, 20, 3), 20)


if __name__ == "__main__":
    unittest.main()
