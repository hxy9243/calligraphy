import unittest

import cv2
import numpy as np

from calligraphy.paint_brush import BrushPainter, complete, fit_brush


class PaintBrushTests(unittest.TestCase):
    def straight(self):
        layer = np.zeros((480, 480), np.float32)
        cv2.line(layer, (70, 220), (400, 220), 1, 24)
        return fit_brush(layer, np.array([1.0, 0.0]))

    def test_straight_rule_removes_wobble(self):
        stroke = self.straight()
        path = np.asarray(stroke["path"])
        self.assertEqual(stroke["kind"], "straight")
        self.assertLess(np.ptp(path[:, 1]), 0.1)
        self.assertTrue(np.all(np.diff(path[:, 0]) >= 0))
        self.assertGreater(complete(stroke)[220, 100:370].min(), 0.99)

    def test_paint_is_monotonic_and_frame_rate_independent(self):
        stroke = self.straight()
        painter = BrushPainter(stroke)
        previous = painter.advance(0)
        self.assertFalse(previous.any())
        for time in np.linspace(0, 1, 41):
            current = painter.advance(time)
            self.assertTrue(np.all(current >= previous))
            previous = current
        np.testing.assert_array_equal(previous, complete(stroke))
        with self.assertRaises(ValueError):
            painter.advance(0.1)

    def test_turn_is_retained_and_paint_connected(self):
        layer = np.zeros((480, 480), np.float32)
        cv2.polylines(layer, [np.array([[80, 120], [360, 120], [360, 380]])], False, 1, 26)
        stroke = fit_brush(layer, np.array([1.0, 1.0]))
        self.assertEqual(stroke["kind"], "curved-or-turn")
        result = complete(stroke)
        self.assertGreater(result[120, 180], 0.9)
        self.assertGreater(result[250, 360], 0.9)
        count, _ = cv2.connectedComponents((result > 0.5).astype("uint8"))
        self.assertEqual(count, 2)

    def test_degenerate_input_rejected(self):
        with self.assertRaises(ValueError):
            fit_brush(np.zeros((480, 480)), [1, 0])
        stroke = self.straight()
        stroke["radius"][0] = -1
        with self.assertRaises(ValueError):
            BrushPainter(stroke)

    def test_explicit_guide_preserves_hook_order(self):
        layer = np.zeros((480, 480), np.float32)
        guide = np.array([[80, 100], [300, 100], [300, 330], [260, 300]])
        cv2.polylines(layer, [guide], False, 1, 22)
        stroke = fit_brush(layer, np.array([-1.0, -1.0]), guide=guide)
        path = np.asarray(stroke["path"])
        self.assertLess(np.linalg.norm(path[0] - guide[0]), 5)
        self.assertLess(np.linalg.norm(path[-1] - guide[-1]), 5)
        self.assertGreater(path[:, 0].max() - path[-1, 0], 25)

    def test_compact_dot_does_not_disappear(self):
        layer = np.zeros((480, 480), np.float32)
        cv2.circle(layer, (200, 200), 2, 1, -1)
        stroke = fit_brush(layer, np.array([1.0, 0.0]))
        self.assertGreater(complete(stroke).sum(), 1)


if __name__ == "__main__":
    unittest.main()
