import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from core.dispatching.navigation import load_mission_page


class MissionNavigationTests(unittest.TestCase):
    def test_mission_page_gets_a_third_attempt_for_transient_load_failures(self):
        class Page:
            def __init__(self):
                self.goto_calls = 0

            async def goto(self, *_args, **_kwargs):
                self.goto_calls += 1
                if self.goto_calls < 3:
                    raise RuntimeError("temporary navigation failure")

            async def wait_for_selector(self, selector, **_kwargs):
                if selector not in {"#missionH1", "#alert_btn"}:
                    raise AssertionError(f"unexpected selector: {selector}")

        page = Page()
        with patch("core.dispatching.navigation.asyncio.sleep", new=AsyncMock()):
            loaded = asyncio.run(
                load_mission_page(
                    page,
                    "123",
                    "Test mission",
                    "https://www.missionchief.com/",
                )
            )

        self.assertTrue(loaded)
        self.assertEqual(page.goto_calls, 3)


if __name__ == "__main__":
    unittest.main()
