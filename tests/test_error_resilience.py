import asyncio
import unittest

from core.concurrency import split_mission_ids_among_threads


class ErrorResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_mission_worker_does_not_discard_successful_workers(self):
        import core.mission_parser as parser

        original = parser.gather_mission_info
        try:
            async def fake_gather(ids, context, thread_id, url, profile, state, progress):
                if thread_id == 1:
                    raise RuntimeError("worker failed")
                return {str(ids[0]): {"mission_name": "kept"}}

            parser.gather_mission_info = fake_gather
            result = await split_mission_ids_among_threads(
                ["one", "two"],
                [object(), object()],
                2,
                "https://example.test/",
            )
        finally:
            parser.gather_mission_info = original

        self.assertEqual(result, {"two": {"mission_name": "kept"}})


if __name__ == "__main__":
    unittest.main()
