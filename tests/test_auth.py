import unittest

from core.auth import classify_login_failure, is_login_page, is_same_service


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


if __name__ == "__main__":
    unittest.main()
