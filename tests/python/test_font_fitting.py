import unittest
from unittest.mock import patch
import numpy as np

from calligraphy.font_fitting import contacts_from_layer, simplify_pairs
from calligraphy.brush_grammar import ContactBrush, complete, validate


class ContactSimplificationTests(unittest.TestCase):
    def test_straight_small_piece_retains_three_original_pairs(self):
        # Three collinear ink pixels, like the detached piece in 聲 stroke 4.
        # Its dense rails are straight enough for RDP to retain just endpoints.
        positions = np.linspace(112, 114, 100)
        pairs = np.stack([np.column_stack([positions, np.full(100,149.)])] * 2, axis=1)
        reduced = simplify_pairs(pairs)
        self.assertGreaterEqual(len(reduced), 3)
        np.testing.assert_array_equal(reduced[0], pairs[0])
        np.testing.assert_array_equal(reduced[-1], pairs[-1])
        for pair in reduced:
            self.assertTrue(any(np.array_equal(pair, p) for p in pairs))
        validate({'contacts': reduced.tolist()})

    def test_fitting_error_identifies_character_and_stroke(self):
        from calligraphy.font_pipeline import fit_glyph
        glyph = {'strokes': ['M 0 0 L 10 10 L 10 0 Z'], 'medians': [[[0,0],[10,10]]]}
        target = np.zeros((480,480), np.float32)
        fields = np.zeros((1,160,160), np.float32)
        layers = np.zeros((1,480,480), np.float32)
        with patch('calligraphy.font_pipeline.registered_fields', return_value=(fields,fields)), \
             patch('calligraphy.font_pipeline.smooth_decomposition', return_value=(layers,layers,layers)), \
             patch('calligraphy.font_pipeline.fit_layer', side_effect=ValueError('invalid contacts')):
            with self.assertRaisesRegex(ValueError, 'Cannot fit 聲 stroke 1: invalid contacts'):
                fit_glyph('聲', target, glyph)

    def test_adaptive_registration_retry_recovers_delicate_stroke(self):
        from calligraphy.font_pipeline import fit_glyph
        glyph = {'strokes': ['M 0 0 L 10 10 L 10 0 Z'], 'medians': [[[0,0],[10,10]]]}
        target = np.zeros((480,480), np.float32)
        target[10:20, 10:20] = 1.0
        fields = np.zeros((1,160,160), np.float32)
        layers_fail = np.zeros((1,480,480), np.float32)
        layers_ok = np.zeros((1,480,480), np.float32)
        layers_ok[0, 10:20, 10:20] = 1.0

        calls = []
        def mock_reg(gray, g, tightness=.3):
            calls.append(tightness)
            return fields, fields

        def mock_decomp(warped, phase, tgt):
            if len(calls) == 1:
                return layers_fail, layers_fail, layers_fail
            return layers_ok, layers_ok, layers_ok

        def mock_fit(layer, progress, name):
            if len(calls) == 1:
                raise ValueError('Empty inferred stroke: ' + name)
            return {'contacts': [[[10,10],[20,20]],[[10,15],[20,25]],[[10,20],[20,30]]], 'corners': []}

        with patch('calligraphy.font_pipeline.registered_fields', side_effect=mock_reg), \
             patch('calligraphy.font_pipeline.smooth_decomposition', side_effect=mock_decomp), \
             patch('calligraphy.font_pipeline.fit_layer', side_effect=mock_fit), \
             patch('calligraphy.font_pipeline.complete_stroke', return_value=layers_ok[0]):
            strokes, metrics = fit_glyph('翁', target, glyph)
            self.assertEqual(len(strokes), 1)
            self.assertEqual(calls, [0.3, 0.5])


    def test_tiny_raster_piece_fits_and_replays_without_discarding_ink(self):
        layer = np.zeros((480,480), np.float32)
        layer[149,112:115] = 1
        layer[148,112:115] = .3
        layer[150,112:115] = .3
        stroke = contacts_from_layer(layer, np.array([[112.,149.],[114.,149.]]), '聲 stroke 4 tiny piece')
        validate(stroke)
        self.assertGreaterEqual(len(stroke['contacts']), 3)
        painter = ContactBrush(stroke)
        previous = np.zeros((480,480), np.float32)
        for progress in np.linspace(0,1,11):
            current = painter.advance(progress)
            self.assertTrue(np.all(current >= previous))
            previous = current.copy()
        np.testing.assert_array_equal(previous, complete(stroke))
        self.assertGreater(previous.sum(), 0)
        self.assertEqual(previous[:140].sum(), 0)
        self.assertEqual(previous[160:].sum(), 0)


if __name__ == '__main__':
    unittest.main()
