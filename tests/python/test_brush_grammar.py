import unittest

import numpy as np

from calligraphy.brush_grammar import ContactBrush, complete, sample, validate


class ContactBrushTests(unittest.TestCase):
    def stroke(self):
        return {
            "contacts": [
                [[20, 24], [20, 16]],
                [[60, 25], [60, 15]],
                [[100, 24], [100, 16]],
            ],
            "tension": 0.65,
        }

    def test_accumulation_is_monotonic_and_frame_rate_independent(self):
        stroke = self.stroke()
        painter = ContactBrush(stroke, size=128)
        previous = painter.advance(0)
        self.assertFalse(previous.any())
        for time in [0.1, 0.3, 0.7, 1.0]:
            current = painter.advance(time)
            self.assertTrue(np.all(current >= previous))
            previous = current
        np.testing.assert_array_equal(previous, ContactBrush(stroke, size=128).advance(1))
        with self.assertRaises(ValueError):
            painter.advance(0.5)

    def test_sampling_preserves_contact_rails(self):
        rails, times = sample(self.stroke())
        np.testing.assert_allclose(rails[0], self.stroke()["contacts"][0])
        np.testing.assert_allclose(rails[-1], self.stroke()["contacts"][-1])
        self.assertTrue(np.all(np.diff(times) >= 0))
        self.assertGreater(complete(self.stroke()).sum(), 0)

    def test_invalid_contacts_rejected(self):
        for contacts in [[], [[[1, 1], [2, 2]]], [[[float("nan"), 1], [2, 2]]] * 3]:
            with self.assertRaises(ValueError):
                validate({"contacts": contacts})


if __name__ == "__main__":
    unittest.main()
