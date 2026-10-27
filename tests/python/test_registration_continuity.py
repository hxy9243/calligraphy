"""Registration must not lose a curved stroke's body while keeping its tips."""
from pathlib import Path
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from calligraphy import font_fitting as fitting
from calligraphy.font_pipeline import target_masks, fit_layer
from calligraphy.contact_stroke import ContactStroke, complete_stroke
from calligraphy.text.glyphs import resolve_glyphs


class ProgressContinuityTests(unittest.TestCase):
    def fields(self):
        phase = np.broadcast_to(np.linspace(0, 1, 160), (160, 160)).copy()[None]
        ink = np.zeros_like(phase)
        ink[:, 70:90, :] = 1
        return ink, phase

    def test_long_interior_loss_is_detected_but_not_endpoint_taper(self):
        reference, phase = self.fields()
        broken = reference.copy()
        broken[:, :, 56:104] = 0
        self.assertEqual(fitting.collapsed_progress_intervals(broken, phase, reference, phase), [(0, 7, 13)])
        tapered = reference.copy()
        tapered[:, :, :48] = 0
        self.assertEqual(fitting.collapsed_progress_intervals(tapered, phase, reference, phase), [])

    def test_disconnected_source_and_uniform_scaling_are_not_collapses(self):
        reference, phase = self.fields()
        reference[:, :, 56:104] = 0
        self.assertEqual(fitting.collapsed_progress_intervals(reference, phase, reference, phase), [])
        narrow = reference.copy()
        narrow[:, 70:80, :] = 0
        self.assertEqual(fitting.collapsed_progress_intervals(narrow, phase, reference, phase), [])

    def test_short_gap_and_tiny_dot_do_not_trigger_retry(self):
        reference, phase = self.fields()
        short = reference.copy()
        short[:, :, 72:88] = 0
        self.assertEqual(fitting.collapsed_progress_intervals(short, phase, reference, phase), [])
        tiny = np.zeros_like(reference)
        tiny[:, 70:72, 78:82] = 1
        self.assertEqual(fitting.collapsed_progress_intervals(tiny, phase, tiny, phase), [])

    def test_candidate_that_worsens_union_is_rejected(self):
        reference, phase = self.fields()
        # Zero flow retains the template; the second mocked flow moves it away.
        calls = []
        def flow(*args, **kwargs):
            calls.append(kwargs['tightness'])
            return np.zeros((2,160,160),np.float32) + (0 if len(calls)==1 else 100)
        with patch.object(fitting, 'template', return_value=(reference,phase)), \
             patch.object(fitting, 'fit_template', return_value=(reference,phase)), \
             patch.object(fitting, 'optical_flow_tvl1', side_effect=flow), \
             patch.object(fitting, 'collapsed_progress_intervals', side_effect=[[(0,7,13)], []]):
            actual,_ = fitting.registered_fields(np.uint8(255*(1-reference[0])), {})
        self.assertEqual(calls,[.3,2.])
        np.testing.assert_array_equal(actual,reference)


class RealFontContinuityTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]

    def target(self, font, char):
        path = self.root/'data/fonts'/font
        if not path.exists():
            self.skipTest('Optional local font not installed: '+font)
        return next(target_masks(path, char))[1]

    def fields(self, font, char):
        target = self.target(font, char)
        glyph = resolve_glyphs(char)[char]
        gray=np.uint8(255*(1-cv2.resize(target,(160,160))))
        return target, glyph, gray

    def test_masa_wind_recovers_continuous_second_stroke(self):
        target,glyph,gray=self.fields('MasaFont-Regular.ttf','風')
        with patch.object(fitting, 'collapsed_progress_intervals', return_value=[]):
            old,old_phase=fitting.registered_fields(gray,glyph)
        diagnostics = {}
        with patch.object(fitting, 'optical_flow_tvl1', wraps=fitting.optical_flow_tvl1) as flow:
            new,new_phase=fitting.registered_fields(gray,glyph,diagnostics=diagnostics)
        self.assertTrue(diagnostics['continuity_repaired'])
        self.assertEqual(diagnostics['selected_tightness'],2.)
        self.assertEqual(diagnostics['remaining_intervals'],[])
        self.assertEqual([call.kwargs['tightness'] for call in flow.call_args_list],[.3,2.])
        self.assertGreaterEqual(fitting.iou(new.max(0), (255-gray)/255), fitting.iou(old.max(0), (255-gray)/255))
        old_layers,_,_=fitting.smooth_decomposition(old,old_phase,target)
        layers,phases,_=fitting.smooth_decomposition(new,new_phase,target)
        for x,y in [(246,140),(249,210),(275,310),(330,386)]:
            self.assertGreater(layers[1,y,x],.9)
        self.assertLess(old_layers[1,210,249],.1)
        stroke=fit_layer(layers[1],phases[1],'wind second')
        self.assertNotIn('segments',stroke)
        painter=ContactStroke(stroke)
        previous=np.zeros((480,480),np.float32)
        for t in [0,.1,.25,.5,.75,1]:
            current=painter.advance(t)
            self.assertTrue(np.all(current>=previous))
            previous=current.copy()
        np.testing.assert_array_equal(previous,complete_stroke(stroke))
        self.assertGreater(previous[210,249],.9)

    def test_regular_hooked_fonts_keep_original_registration(self):
        for font,char in [('LXGWWenKaiTC-Regular.ttf','風'),('EduKai.ttf','風'),
                          ('MasaFont-Regular.ttf','永'),('LXGWWenKaiTC-Regular.ttf','九')]:
            with self.subTest(font=font,char=char):
                _,glyph,gray=self.fields(font,char)
                with patch.object(fitting,'optical_flow_tvl1',wraps=fitting.optical_flow_tvl1) as flow:
                    actual,phase=fitting.registered_fields(gray,glyph)
                self.assertEqual(flow.call_count,1)
                with patch.object(fitting,'collapsed_progress_intervals',return_value=[]):
                    expected,expected_phase=fitting.registered_fields(gray,glyph)
                np.testing.assert_array_equal(actual,expected)
                np.testing.assert_array_equal(phase,expected_phase)
