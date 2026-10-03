import copy
import unittest

import numpy as np

from calligraphy.stroke_ir import render_program, validate_program
from calligraphy.stroke_regularization import regularize_program


def program(centres, widths, corners=()):
    centres = np.asarray(centres, float)
    widths = np.asarray(widths, float)
    tangent = np.gradient(centres, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    pairs = np.stack([
        centres + normal * widths[:, None] / 2,
        centres - normal * widths[:, None] / 2,
    ], axis=1)
    return {
        "schemaVersion": "kai-stroke-ir/0.2",
        "character": "永",
        "script": "kai",
        "provenance": {"source": "synthetic-test", "inferred": True},
        "strokes": [
            {
                "id": "s1",
                "kind": "test",
                "duration": 1,
                "liftAfter": 0,
                "geometry": {
                    "type": "paired-contacts",
                    "stations": pairs.tolist(),
                    "corners": list(corners),
                    "tension": 0.5,
                },
            }
        ],
        "relations": [],
    }


class StrokeRegularizationTests(unittest.TestCase):
    def test_isolated_overlap_protrusion_is_reduced_without_mutating_input(self):
        x = np.linspace(0.12, 0.88, 13)
        centres = np.column_stack([x, np.full_like(x, 0.5)])
        centres[6, 1] = 0.64
        widths = np.full(13, 0.08)
        widths[6] = 0.28
        original = program(centres, widths)
        snapshot = copy.deepcopy(original)
        result, report = regularize_program(original)
        self.assertEqual(original, snapshot)
        validate_program(result)
        new = np.asarray(result["strokes"][0]["geometry"]["stations"])
        new_centres = new.mean(axis=1)
        new_widths = np.linalg.norm(new[:, 0] - new[:, 1], axis=1)
        self.assertLess(abs(new_centres[6, 1] - 0.5), abs(centres[6, 1] - 0.5) * 0.45)
        self.assertLess(new_widths[6], 0.18)
        self.assertGreater(report["strokes"][0]["spikesLimited"], 0)
        self.assertLess(report["strokes"][0]["curvatureAfter"], report["strokes"][0]["curvatureBefore"])
        self.assertLess(report["strokes"][0]["widthRoughnessAfter"], report["strokes"][0]["widthRoughnessBefore"])

    def test_broad_turn_hook_and_width_are_retained(self):
        centres = [
            [0.18, 0.25], [0.3, 0.25], [0.42, 0.25], [0.54, 0.28], [0.61, 0.38],
            [0.62, 0.5], [0.61, 0.62], [0.57, 0.73], [0.48, 0.79],
        ]
        widths = [0.06, 0.07, 0.09, 0.14, 0.17, 0.18, 0.17, 0.13, 0.06]
        source = program(centres, widths, corners=(4,))
        result, report = regularize_program(source)
        contacts = np.asarray(result["strokes"][0]["geometry"]["stations"])
        new_centres = contacts.mean(axis=1)
        new_widths = np.linalg.norm(contacts[:, 0] - contacts[:, 1], axis=1)
        self.assertGreater(new_centres[-1, 1] - new_centres[4, 1], 0.3)
        self.assertLess(new_centres[-1, 0], new_centres[4, 0])
        self.assertGreater(np.mean(new_widths[3:7]), 1.7 * np.mean(new_widths[[0, 1, 7, 8]]))
        self.assertEqual(report["strokes"][0]["cubicSpans"], 2)
        self.assertEqual(report["strokes"][0]["spikesLimited"], 0)

    def test_guide_anchors_broad_center_shape_and_output_stays_in_bounds(self):
        x = np.linspace(0.02, 0.92, 11)
        target_centres = np.column_stack([x, 0.14 + 0.3 * x])
        target_centres[5, 1] += 0.15
        guide_centres = np.column_stack([x, 0.14 + 0.3 * x])
        target = program(target_centres, np.full(11, 0.1))
        guide = program(guide_centres, np.full(11, 0.08))
        unguided, _ = regularize_program(target)
        guided, report = regularize_program(target, guide)
        u = np.asarray(unguided["strokes"][0]["geometry"]["stations"]).mean(axis=1)
        g_contacts = np.asarray(guided["strokes"][0]["geometry"]["stations"])
        g = g_contacts.mean(axis=1)
        desired = guide_centres[5]
        self.assertLess(np.linalg.norm(g[5] - desired), np.linalg.norm(u[5] - desired))
        self.assertTrue(report["strokes"][0]["guideUsed"])
        self.assertGreaterEqual(float(g_contacts.min()), 0)
        self.assertLessEqual(float(g_contacts.max()), 1)
        self.assertGreater(render_program(guided, 1, size=96).sum(), 0)

    def test_rejects_legacy_program_and_reports_reproducible_configuration(self):
        p = program([[0.2, 0.2], [0.5, 0.5], [0.8, 0.8]], [0.05, 0.06, 0.05])
        _, report = regularize_program(p)
        self.assertEqual(report["method"], "piecewise-cubic-ribbon/1")
        self.assertEqual(report["config"]["maximumPolynomialDegreePerSpan"], 3)
        self.assertIn("not a physical brush simulation", report["claim"])
        p["schemaVersion"] = "kai-stroke-ir/0.1"
        with self.assertRaises(ValueError):
            regularize_program(p)

    def test_duplicate_interior_midpoints_use_nearest_valid_direction(self):
        centres = [
            [0.2, 0.3], [0.35, 0.3], [0.5, 0.3], [0.55, 0.3], [0.65, 0.3], [0.8, 0.3]
        ]
        source = program(centres, [0.06] * len(centres))
        source["strokes"][0]["geometry"]["stations"][3] = copy.deepcopy(
            source["strokes"][0]["geometry"]["stations"][2]
        )
        result, _ = regularize_program(source)
        validate_program(result)


if __name__ == "__main__":
    unittest.main()
