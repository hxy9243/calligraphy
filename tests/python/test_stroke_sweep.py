import copy
import unittest

import numpy as np

from calligraphy.stroke_sweep import (
    compile_smooth_program, render_smooth_program, validate_smooth_program,
)


def source():
    x = np.linspace(.15, .85, 15)
    centres = np.column_stack((x, np.full_like(x, .5)))
    centres[7, 1] = .62  # synthetic narrow middle protrusion
    normal = np.tile([0., 1.], (len(x), 1))
    widths = np.full(len(x), .06); widths[[0, -1]] = .008
    pairs = np.stack((centres + normal * widths[:, None] / 2,
                      centres - normal * widths[:, None] / 2), axis=1)
    return {"schemaVersion": "kai-stroke-ir/0.2", "character": "永", "script": "kai",
            "provenance": {"source": "synthetic"}, "relations": [],
            "strokes": [{"id": "s1", "kind": "test", "duration": 1, "liftAfter": .2,
                         "geometry": {"type": "paired-contacts", "stations": pairs.tolist(),
                                      "corners": [], "tension": .5}}]}


class StrokeSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program, cls.report = compile_smooth_program(source())

    def test_compile_is_frozen_bounded_and_reduces_radius_roughness(self):
        self.assertIs(validate_smooth_program(self.program), self.program)
        item = self.report["strokes"][0]
        self.assertLess(item["radiusRoughnessAfter"], item["radiusRoughnessBefore"])
        geometry = self.program["strokes"][0]["geometry"]
        radius = np.asarray(geometry["radius"])
        self.assertGreaterEqual(radius[0], .4 * np.percentile(radius, 75) - 1e-6)
        self.assertGreaterEqual(radius[-1], .4 * np.percentile(radius, 75) - 1e-6)
        self.assertNotIn("mask", geometry)

    def test_replay_is_stateless_monotone_and_lift_is_blank(self):
        frames = [render_smooth_program(self.program, p, 96) for p in (0, .2, .5, .84, .9, 1)]
        for before, after in zip(frames, frames[1:]):
            self.assertTrue(np.all(after >= before))
        np.testing.assert_array_equal(frames[-2], frames[-1])
        np.testing.assert_array_equal(render_smooth_program(self.program, .5, 96), frames[2])

    def test_validation_rejects_nonfinite_and_mismatched_frozen_geometry(self):
        for mutate in (
            lambda p: p["strokes"][0]["geometry"]["path"][0].__setitem__(0, float("nan")),
            lambda p: p["strokes"][0]["geometry"]["radius"].pop(),
        ):
            bad = copy.deepcopy(self.program); mutate(bad)
            with self.assertRaises(ValueError):
                validate_smooth_program(bad)

        stationary = copy.deepcopy(self.program)
        stationary["strokes"][0]["geometry"]["path"] = [stationary["strokes"][0]["geometry"]["path"][0]] * len(
            stationary["strokes"][0]["geometry"]["path"])
        with self.assertRaisesRegex(ValueError, "must travel"):
            validate_smooth_program(stationary)


if __name__ == "__main__":
    unittest.main()
