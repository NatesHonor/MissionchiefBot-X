import unittest
from types import SimpleNamespace

from core.dispatching.dispatcher import dispatch_delay_seconds


class DispatchPacingTests(unittest.TestCase):
    def test_missing_dispatch_delay_keeps_backward_compatible_zero_pause(self):
        self.assertEqual(dispatch_delay_seconds(SimpleNamespace()), 0)

    def test_dispatch_delay_is_normalized_to_a_non_negative_integer(self):
        self.assertEqual(
            dispatch_delay_seconds(SimpleNamespace(dispatch_delay="15")),
            15,
        )
        self.assertEqual(
            dispatch_delay_seconds(SimpleNamespace(dispatch_delay=-4)),
            0,
        )


if __name__ == "__main__":
    unittest.main()
