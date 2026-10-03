"""Regression contracts for bounded mask-to-contact fitting."""
import unittest

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
