"""Bounded source-directed fallback for ink whose registration phase collapsed."""
import unittest
from pathlib import Path

import cv2
import numpy as np

from calligraphy.contact_stroke import ContactStroke, complete_stroke
from calligraphy.font_fitting import compact_dot_guide, iou, ordered_guide
from calligraphy.font_pipeline import fit_layer, fit_glyph, target_masks
from calligraphy.text.glyphs import load_bundled_glyphs


class CompactDotFallbackTests(unittest.TestCase):
    def dot(self):
        layer = np.zeros((480, 480), np.float32)
        cv2.ellipse(layer, (240, 240), (10, 5), 25, 0, 360, 1, -1)
        return layer

    def test_real_ink_is_retained_and_replay_is_monotonic(self):
        layer = self.dot()
        phase = np.ones_like(layer)
        with self.assertRaisesRegex(ValueError, 'degenerate stroke'):
            ordered_guide(layer, phase)
        stroke = fit_layer(layer, phase, 'dot', fallback_direction=[1, 1])
        self.assertEqual(stroke['guide_inference'], 'compact-dot-template-direction')
        self.assertGreater(iou(complete_stroke(stroke), layer), .8)
        painter = ContactStroke(stroke)
        before = np.zeros_like(layer)
        for progress in np.linspace(0, 1, 13):
            after = painter.advance(progress)
            self.assertTrue(np.all(after >= before))
            before = after.copy()
        np.testing.assert_array_equal(before, complete_stroke(stroke))

    def test_template_direction_orients_same_ink_geometry(self):
        layer = self.dot()
        forward = compact_dot_guide(layer, [1, 1])
        reverse = compact_dot_guide(layer, [-1, -1])
        np.testing.assert_allclose(forward, reverse[::-1])
        self.assertGreater(np.dot(forward[-1] - forward[0], [1, 1]), 0)

    def test_meaningful_guards_are_not_relaxed(self):
        for layer, direction in [(np.zeros((480, 480)), [1, 0]),
                                 (np.ones((480, 480)), [1, 0]),
                                 (self.dot(), [0, 0]),
                                 (self.dot(), [np.nan, 1]),
                                 (np.full((480, 480), np.nan), [1, 0])]:
            with self.subTest(direction=direction):
                with self.assertRaises(ValueError):
                    compact_dot_guide(layer, direction)
        with self.assertRaisesRegex(ValueError, 'finite matching'):
            fit_layer(self.dot(), np.full((480, 480), np.nan), 'invalid', fallback_direction=[1, 0])
        singleton = np.zeros((480, 480)); singleton[240, 240] = 1
        with self.assertRaises(ValueError):
            compact_dot_guide(singleton, [1, 0])
        with self.assertRaisesRegex(ValueError, 'Empty inferred stroke'):
            fit_layer(np.zeros((480, 480)), np.ones((480, 480)), 'empty', fallback_direction=[1, 0])

    def test_regular_progress_keeps_exact_existing_geometry(self):
        layer = self.dot()
        phase = np.broadcast_to(np.linspace(0, 1, 480), layer.shape)
        original = fit_layer(layer, phase, 'dot')
        relaxed = fit_layer(layer, phase, 'dot', fallback_direction=[1, 0])
        self.assertEqual(original, relaxed)
        self.assertNotIn('guide_inference', relaxed)

    def test_disconnected_ink_keeps_separate_segments(self):
        layer = np.zeros((480, 480), np.float32)
        layer[237:243, 231:237] = 1
        layer[237:243, 246:252] = 1
        stroke = fit_layer(layer, np.ones_like(layer), 'two dots', fallback_direction=[1, 0])
        self.assertEqual(len(stroke['segments']), 2)
        self.assertFalse((complete_stroke(stroke)[237:243, 239:244] > .5).any())

    def test_masafont_frost_preserves_stroke_count_and_marks_inference(self):
        font = Path(__file__).resolve().parents[2] / 'data/fonts/MasaFont-Regular.ttf'
        if not font.is_file():
            self.skipTest('Separately provisioned MasaFont source is unavailable')
        glyph = load_bundled_glyphs()['霜']
        _, target = next(target_masks(font, ['霜']))
        strokes, metrics = fit_glyph('霜', target, glyph)
        self.assertEqual(len(strokes), len(glyph['strokes']))
        self.assertGreater(metrics['silhouette_iou'], .9)
        self.assertIn(7, metrics['guide_fallback_strokes'])
        self.assertTrue(metrics['review_required'])
        self.assertEqual([s['name'] for s in strokes], [f'霜 stroke {i+1}' for i in range(len(strokes))])
        for number in metrics['guide_fallback_strokes']:
            stroke = strokes[number - 1]
            painter = ContactStroke(stroke)
            before = np.zeros_like(target)
            for progress in np.linspace(0, 1, 9):
                after = painter.advance(progress)
                self.assertTrue(np.all(after >= before))
                before = after.copy()
            np.testing.assert_array_equal(before, complete_stroke(stroke))


if __name__ == '__main__':
    unittest.main()
