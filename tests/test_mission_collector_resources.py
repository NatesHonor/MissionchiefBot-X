import unittest

from core.mission_collector import scan_event_resources


class MissionCollectorResourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_event_scan_does_not_touch_the_page(self):
        self.assertEqual(await scan_event_resources(None, "https://example.test/", False), 0)

    async def test_enabled_event_scan_reports_the_collected_count(self):
        import core.mission_collector as collector

        original = collector.collect_special_resources
        try:
            async def fake_collect(page, base_url):
                self.assertEqual(page, "page")
                self.assertEqual(base_url, "https://example.test/")
                return 2

            collector.collect_special_resources = fake_collect
            self.assertEqual(
                await scan_event_resources("page", "https://example.test/", True),
                2,
            )
        finally:
            collector.collect_special_resources = original
