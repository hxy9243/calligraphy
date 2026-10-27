import unittest

from calligraphy.text import (
    create_text_plan,
    is_han,
    is_punctuation,
    layout_text,
    load_bundled_glyphs,
    parse_text,
    resolve_glyphs,
    validate_glyph,
)


class TextPipelineTests(unittest.TestCase):
    def setUp(self):
        self.counts = {"明": 8, "月": 4, "永": 5, "清": 11}

    def test_han_and_punctuation_predicates(self):
        self.assertTrue(is_han("明"))
        self.assertTrue(is_han("永"))
        self.assertTrue(is_han("龘"))
        self.assertTrue(is_han("𠮷"))
        self.assertFalse(is_han("A"))
        self.assertFalse(is_han("1"))
        self.assertFalse(is_han("，"))
        self.assertTrue(is_punctuation("，"))
        self.assertTrue(is_punctuation("。"))
        self.assertFalse(is_punctuation("明"))

    def test_parse_text_preserves_repeated_glyphs_and_lines(self):
        res = parse_text(" 明明，月\r\n永。")
        self.assertEqual(res["lines"], [["明", "明", " ", "月"], ["永", " "]])
        self.assertEqual(res["characters"], ["明", "明", "月", "永"])
        self.assertEqual(res["uniqueCharacters"], ["明", "月", "永"])
        self.assertIn("，", res["omitted"])
        self.assertIn("。", res["omitted"])

        omit_res = parse_text("明，月", punctuation="omit")
        self.assertEqual(omit_res["lines"], [["明", "月"]])
        self.assertEqual(parse_text("明，月", punctuation="break")["lines"], [["明"], ["月"]])
        self.assertEqual(parse_text("，明！？月。\n，！")["lines"], [[" ", "明", " ", " ", "月", " "]])

        for bad in ["", "   ", " ，。 ", "明A", "明🙂"]:
            with self.assertRaises(ValueError):
                parse_text(bad)

        with self.assertRaises(ValueError):
            parse_text("永" * 513)

        with self.assertRaises(ValueError):
            parse_text("永", punctuation="invalid")

        with self.assertRaisesRegex(ValueError, "512-cell"):
            parse_text("永" + "，" * 512)

    def test_punctuation_reserves_cells_without_glyphs_or_timing(self):
        for direction, axis, cross_axis in [("vertical-rl", "y", "x"), ("horizontal-lr", "x", "y")]:
            with self.subTest(direction=direction):
                layout = {"direction": direction, "charactersPerLine": 8, "font_size": 64}
                plan = create_text_plan("明，月", self.counts, layout=layout, inscription="永、清")
                plain = create_text_plan("明月", self.counts, layout=layout, inscription="永清")
                self.assertEqual([p["character"] for p in plan["schedule"]], list("明月永清"))
                self.assertEqual(plan["duration"], plain["duration"])
                for first, second in [plan["schedule"][:2], plan["schedule"][2:]]:
                    self.assertEqual(first[cross_axis], second[cross_axis])
                    self.assertAlmostEqual(second[axis] - first[axis], first["size"] * 1.18 * 2)

    def test_punctuation_gaps_count_toward_wrapping(self):
        plan = create_text_plan("明，月", self.counts, layout={"charactersPerLine": 2})
        self.assertEqual([p["line"] for p in plan["schedule"]], [0, 1])
        self.assertEqual([p["row"] for p in plan["schedule"]], [0, 0])

    def test_layout_vertical_right_to_left(self):
        p = create_text_plan(
            text="明月永清明月",
            stroke_counts=self.counts,
            layout={"width": 600, "height": 800, "charactersPerLine": 2},
        )
        self.assertEqual([e["character"] for e in p["schedule"]], list("明月永清明月"))
        # Vertical right-to-left: column 0 is rightmost
        self.assertGreater(p["schedule"][0]["x"], p["schedule"][2]["x"])
        self.assertGreater(p["schedule"][2]["x"], p["schedule"][4]["x"])
        self.assertEqual(p["schedule"][0]["x"], p["schedule"][1]["x"])
        self.assertLess(p["schedule"][0]["y"], p["schedule"][1]["y"])

        for e in p["schedule"]:
            self.assertGreaterEqual(e["x"], 0)
            self.assertGreaterEqual(e["y"], 0)
            self.assertLessEqual(e["x"] + e["size"], p["width"] + 1e-6)
            self.assertLessEqual(e["y"] + e["size"], p["height"] + 1e-6)

    def test_layout_horizontal_left_to_right(self):
        p = create_text_plan(
            text="明月\n永清",
            stroke_counts=self.counts,
            layout={"direction": "horizontal-lr", "charactersPerLine": 5},
        )
        self.assertLess(p["schedule"][0]["x"], p["schedule"][1]["x"])
        self.assertEqual(p["schedule"][0]["y"], p["schedule"][1]["y"])
        self.assertGreater(p["schedule"][2]["y"], p["schedule"][0]["y"])

    def test_timing_and_schedule(self):
        p = create_text_plan(
            text="明月明",
            stroke_counts=self.counts,
            timing={"intro": 1.0, "outro": 2.0, "characterGap": 0.5, "strokeSeconds": 0.25},
        )
        schedule_intervals = [[e["start"], e["end"]] for e in p["schedule"]]
        self.assertEqual(schedule_intervals, [[1.0, 3.0], [3.5, 4.5], [5.0, 7.0]])
        self.assertEqual(p["duration"], 9.0)
        self.assertEqual(p["schemaVersion"], 1)

    def test_invalid_parameters_fail_before_render(self):
        for bad_layout in [
            {"width": 0},
            {"width": 10000},
            {"margin": 800},
            {"gap": -1},
            {"direction": "diagonal"},
        ]:
            with self.assertRaises(ValueError):
                create_text_plan("永", stroke_counts=self.counts, layout=bad_layout)

        for bad_timing in [
            {"strokeSeconds": 0},
            {"intro": -1},
            {"characterGap": -1},
        ]:
            with self.assertRaises(ValueError):
                create_text_plan("永", stroke_counts=self.counts, timing=bad_timing)

        with self.assertRaises(ValueError):
            create_text_plan("明月", stroke_counts={})

        with self.assertRaises(ValueError):
            create_text_plan("永", stroke_counts={"永": 0})

    def test_resolve_and_validate_glyphs(self):
        bundled = load_bundled_glyphs()
        self.assertIn("永", bundled)
        self.assertIn("明", bundled)

        resolved = resolve_glyphs("明月")
        self.assertIn("明", resolved)
        self.assertIn("月", resolved)

        with self.assertRaises(ValueError):
            resolve_glyphs("天地", glyphs={"永": bundled["永"]}, fetch_missing=False)

        bad_glyph = {"strokes": [], "medians": []}
        with self.assertRaises(TypeError):
            validate_glyph("永", bad_glyph)


if __name__ == "__main__":
    unittest.main()
