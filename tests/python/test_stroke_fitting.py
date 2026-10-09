"""Regression contracts for bounded mask-to-contact fitting."""
import unittest
import json
from pathlib import Path

import cv2

import numpy as np
from calligraphy.brush_grammar import ContactBrush
from calligraphy.stroke_fitting import fit_contact_stroke
from calligraphy.rail_alignment import align_rails


class StrokeFittingTests(unittest.TestCase):
    def test_fitted_geometry_replays_without_reference(self):
        target = np.zeros((480, 480), bool)
        target[180:205, 60:420] = True
        result = fit_contact_stroke(target, np.array([[.125, .4], [.875, .4]]))
        contacts = (np.asarray(result['contacts']) * 480).tolist()
        painter = ContactBrush({'contacts': contacts, 'corners': [], 'tension': 0})
        partial = painter.advance(.4)
        final = painter.advance(1)
        mask = final > .5
        self.assertGreaterEqual(np.count_nonzero(mask & target) / np.count_nonzero(mask | target), .95)
        self.assertTrue(np.all(partial <= final))
        self.assertGreater(float(final.sum()), float(partial.sum()))
        self.assertLessEqual(len(contacts), 64)
        self.assertTrue(result['report']['prefixConnected'])
        self.assertEqual(result['report']['engine']['engine_version'], 'kai-fitted-v1')

    def test_unsupported_topology_is_explicit(self):
        target = np.zeros((480, 480), bool)
        target[100:200, 100:200] = True
        target[130:160, 130:160] = False
        guide = np.array([[.22, .25], [.4, .35]])
        with self.assertRaisesRegex(ValueError, 'holes'):
            fit_contact_stroke(target, guide)
        target[130:160, 130:160] = True
        target[300:320, 300:320] = True
        with self.assertRaisesRegex(ValueError, 'one connected'):
            fit_contact_stroke(target, guide)

    def test_tiny_nearby_satellite_is_scored_against_original(self):
        target = np.zeros((480, 480), bool)
        target[180:205, 60:420] = True
        target[207, 419] = True  # Three pixels from the main stroke.
        original = target.copy()
        result = fit_contact_stroke(target, np.array([[.125, .4], [.875, .4]]))
        report = result['report']
        self.assertEqual(report['inputComponents'], 2)
        self.assertEqual(report['ignoredSatellitePixels480'], 1)
        self.assertEqual(report['maxSatelliteDistance480'], 3)
        self.assertTrue(report['scoredAgainstOriginalTarget'])
        np.testing.assert_array_equal(target, original)
        rendered = ContactBrush({'contacts': result['contacts480'], 'corners': [], 'tension': 0}).advance(1) > .5
        expected = np.count_nonzero(rendered & target) / np.count_nonzero(rendered | target)
        self.assertEqual(report['iou480'], expected)
        self.assertTrue(report['prefixConnected'])
        self.assertTrue(report['monotonic'])

    def test_satellite_tolerance_is_bounded_by_total_area_ratio_and_distance(self):
        guide = np.array([[.125, .4], [.875, .4]])
        cases = []
        area = np.zeros((480, 480), bool)
        area[180:205, 60:420] = True
        area[207, 60:69] = True  # Nine pixels in total, even though nearby.
        cases.append(area)
        distributed = area.copy()
        distributed[207] = False
        distributed[207, 60:78:2] = True  # Nine separate one-pixel components.
        cases.append(distributed)
        far = area.copy()
        far[207] = False
        far[208, 419] = True  # Four pixels away.
        cases.append(far)
        ratio = np.zeros((480, 480), bool)
        ratio[180:190, 60:70] = True
        ratio[192, 69] = True  # Exactly 1%: fail closed.
        cases.append(ratio)
        for target in cases:
            with self.subTest(ink=int(target.sum())):
                with self.assertRaisesRegex(ValueError, 'one connected'):
                    fit_contact_stroke(target, guide)

    def test_eight_nearby_pixels_are_allowed_but_main_holes_are_not(self):
        target = np.zeros((480, 480), bool)
        target[180:205, 60:420] = True
        target[207, 60:68] = True
        guide = np.array([[.125, .4], [.875, .4]])
        result = fit_contact_stroke(target, guide)
        self.assertEqual(result['report']['ignoredSatellitePixels480'], 8)
        target[188:195, 200:210] = False
        with self.assertRaisesRegex(ValueError, 'holes'):
            fit_contact_stroke(target, guide)

    def test_que_tenth_stroke_rasterization_regression(self):
        from calligraphy.font_fitting import template
        glyph = json.loads((Path(__file__).parent / 'fixtures/que-hanzi-writer-2.0.1.json').read_text())
        layers, _, guides = template(glyph, return_guides=True)
        target = cv2.resize(layers[9], (480, 480), interpolation=cv2.INTER_LINEAR) > .5
        count, _, stats, _ = cv2.connectedComponentsWithStats(target.astype(np.uint8), connectivity=8)
        self.assertEqual(count, 3)
        self.assertEqual(sorted(stats[1:, cv2.CC_STAT_AREA].tolist()), [1, 993])
        result = fit_contact_stroke(target, guides[9], target_iou=.95)
        self.assertGreaterEqual(result['report']['iou480'], .95)
        self.assertEqual(result['report']['ignoredSatellitePixels480'], 1)
        self.assertTrue(result['report']['prefixConnected'])
        self.assertTrue(result['report']['monotonic'])

    def test_empty_target_remains_explicit(self):
        with self.assertRaisesRegex(ValueError, 'no ink'):
            fit_contact_stroke(np.zeros((480, 480), bool), np.array([[.2, .2], [.4, .4]]))

    def test_invalid_guides_and_station_budget_fail(self):
        target = np.zeros((480, 480), bool)
        target[100:200, 100:200] = True
        with self.assertRaisesRegex(ValueError, 'finite'):
            fit_contact_stroke(target, np.array([[np.nan, .25], [.4, .35]]))
        rails = np.array([[100., 100.], [200., 200.]])
        with self.assertRaisesRegex(ValueError, r'\[3,64\]'):
            align_rails(rails, rails, target, np.array([[.2, .2], [.4, .4]]), stations=2)


if __name__ == '__main__':
    unittest.main()
