"""Glyph placement, paper lines and stamp metadata share one resolved grid."""
import json
import unittest

import numpy as np

from calligraphy.paper import get_stamp_preview_meta, render_writing_paper
from calligraphy.spec import Appearance, RenderPlan, SceneSpec


class RuledLayoutTests(unittest.TestCase):
    def test_automatic_and_manual_lanes_align_main_text_and_inscriptions(self):
        for direction in ("vertical-rl", "horizontal-lr"):
            for count in (None, 4, 7, 8):
                for style in ("xuan", "wusi", "gold"):
                    with self.subTest(direction=direction, count=count, style=style):
                        spec = SceneSpec("明，月\n月明", inscription="永明\n月永",
                            layout={"width": 720, "height": 960, "direction": direction,
                                    "font_size": 68, "zigzag": True},
                            appearance=Appearance(paper_style=style, paper_line_count=count))
                        plan = RenderPlan.create(spec, {"明": 8, "月": 4, "永": 5})
                        grid = plan.paper_grid
                        self.assertEqual([p["character"] for p in plan.schedule], list("明月月明永明月永"))
                        if count is not None:
                            self.assertEqual(grid["n_lanes"], count)
                        else:
                            self.assertGreaterEqual(grid["n_lanes"], 4)
                            self.assertEqual((grid["n_lanes"] - 4) % 2, 0)
                        axis = "x" if direction == "vertical-rl" else "y"
                        by_line = {}
                        for p in plan.schedule:
                            center = p[axis] + p["size"] / 2
                            self.assertLess(min(abs(center - lane) for lane in grid["lane_centers"]), .001)
                            self.assertLess(p["size"], grid["lane_width"])
                            by_line.setdefault(p["line"], set()).add(round(center, 2))
                        self.assertEqual(len(by_line), 4)
                        self.assertTrue(all(len(centers) == 1 for centers in by_line.values()))
                        centers = [next(iter(by_line[line])) for line in sorted(by_line)]
                        self.assertEqual(centers, sorted(centers, reverse=direction == "vertical-rl"))
                        # Punctuation retains a full slot along the writing lane.
                        along = "y" if axis == "x" else "x"
                        rigid = RenderPlan.create(SceneSpec(spec.text, inscription=spec.inscription,
                            layout={**spec.layout, "zigzag": False}, appearance=spec.appearance),
                            {"明": 8, "月": 4, "永": 5})
                        a, b = rigid.schedule[:2]
                        self.assertAlmostEqual(b[along] - a[along], 2 * a["size"] * 1.18)

    def test_preview_stamp_and_serialized_paper_use_the_plan_grid(self):
        for direction in ("vertical-rl", "horizontal-lr"):
            params = dict(text="明月\n月明", inscription="永", width=720, height=960,
                          direction=direction, font_size=68, paper_line_count=7, punctuation="gap")
            spec = SceneSpec(params["text"], inscription=params["inscription"],
                layout={k: params[k] for k in ("width", "height", "direction", "font_size")},
                appearance=Appearance(paper_line_count=7))
            plan = RenderPlan.create(spec, {"明": 8, "月": 4, "永": 5})
            meta = get_stamp_preview_meta(params)
            self.assertEqual(meta["lane_centers"], list(plan.paper_grid["lane_centers"]))
            serialized = json.loads(json.dumps(plan.to_dict()))
            np.testing.assert_array_equal(
                render_writing_paper(720, 960, spec.appearance, plan),
                render_writing_paper(720, 960, spec.appearance, serialized))

    def test_lane_overflow_is_rejected_when_fitting_is_disabled(self):
        for layout, count in [({"font_size": 140, "fit": False}, 16), ({"font_size": 48}, 1)]:
            with self.assertRaises(ValueError):
                RenderPlan.create(SceneSpec("明\n月", layout=layout,
                    appearance=Appearance(paper_line_count=count)), {"明": 8, "月": 4})

    def test_unruled_pages_keep_their_existing_layout(self):
        for style in ("plain", "unruled"):
            base = SceneSpec("明，月\n明", layout={"font_size": 68}, appearance=Appearance(paper_style=style))
            manual = SceneSpec(base.text, layout=base.layout, appearance=Appearance(paper_style=style, paper_line_count=8))
            a, b = (RenderPlan.create(spec, {"明": 8, "月": 4}) for spec in (base, manual))
            self.assertEqual(a.schedule, b.schedule)
            self.assertIsNone(a.paper_grid)


if __name__ == "__main__":
    unittest.main()
