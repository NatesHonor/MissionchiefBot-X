import asyncio
import unittest
from unittest.mock import patch

from core.auth import classify_login_failure, is_login_page, is_same_service, login_all


class AuthHelperTests(unittest.TestCase):
    def test_service_check_allows_www_redirect_but_rejects_other_hosts(self):
        self.assertTrue(
            is_same_service(
                "https://www.missionchief.com/",
                "https://missionchief.com/dashboard",
            )
        )
        self.assertFalse(
            is_same_service(
                "https://www.missionchief.com/",
                "https://example.com/dashboard",
            )
        )

    def test_login_page_and_localized_failure_detection(self):
        self.assertTrue(is_login_page("https://missionchief.com/users/sign_in"))
        self.assertFalse(is_login_page("https://missionchief.com/"))
        self.assertEqual(
            classify_login_failure("Ungültige Email oder Passwort"),
            "Invalid credentials",
        )
        self.assertIsNone(classify_login_failure("Welcome back"))

    def test_unexpected_browser_task_failure_becomes_a_failure_result(self):
        async def fail_once(**kwargs):
            raise RuntimeError("browser closed unexpectedly")

        with patch("core.auth.login_single", fail_once):
            results = asyncio.run(login_all("user", "password", 1, None, "https://example.com/"))

        self.assertEqual(results, [("Failure", "browser closed unexpectedly", None)])


if __name__ == "__main__":
    unittest.main()
