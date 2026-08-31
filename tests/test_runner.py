import asyncio
import sys
import unittest
from types import SimpleNamespace

sys.modules.setdefault("art", SimpleNamespace())

from core.runner import run_parallel_runtime_loops


class RuntimeLoopTests(unittest.TestCase):
    def test_mission_and_transport_loops_start_together(self):
        async def exercise():
            stop_event = asyncio.Event()
            started = []

            async def loop(name):
                started.append(name)
                while not stop_event.is_set():
                    await asyncio.sleep(0)

            async def stop_after_both_start():
                while len(started) < 2:
                    await asyncio.sleep(0)
                stop_event.set()

            await asyncio.gather(
                run_parallel_runtime_loops(
                    [("mission", lambda: loop("mission")), ("transport", lambda: loop("transport"))],
                    stop_event,
                ),
                stop_after_both_start(),
            )
            return started

        self.assertEqual(set(asyncio.run(exercise())), {"mission", "transport"})


if __name__ == "__main__":
    unittest.main()
