import json
from pathlib import Path
import unittest

from calligraphy import (
    STYLE_PRESETS,
    create_animation_gif,
    create_vector_player,
    render_character_svg,
    render_scene_svg,
    render_style_comparison_svg,
    render_timeline_images,
    resolve_style_expansion,
    trace_polyline,
)


class AnimationTests(unittest.TestCase):
    def setUp(self):
        assets_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "data"
        with open(assets_dir / "yong.json", "r", encoding="utf-8") as f:
            self.yong_data = json.load(f)
        with open(assets_dir / "poem-characters.json", "r", encoding="utf-8") as f:
            self.poem_data = json.load(f)

    def test_trace_polyline(self):
        pts = [[0, 0], [10, 0], [10, 10]]
        path0, tip0 = trace_polyline(pts, 0.0)
        self.assertEqual(path0, "M 0.00 0.00")
        self.assertEqual(tip0, [0.0, 0.0])

        path_half, tip_half = trace_polyline(pts, 0.5)
        self.assertEqual(tip_half, [10.0, 0.0])
        self.assertIn("M 0.00 0.00 L 10.00 0.00", path_half)

        path_full, tip_full = trace_polyline(pts, 1.0)
        self.assertEqual(tip_full, [10.0, 10.0])

    def test_style_presets(self):
        self.assertEqual(resolve_style_expansion("standard"), 0.0)
        self.assertEqual(resolve_style_expansion("yan"), 16.48)
        self.assertEqual(resolve_style_expansion("slender"), -8.0)
        self.assertEqual(resolve_style_expansion(expansion=5.5), 5.5)
        with self.assertRaises(ValueError):
            resolve_style_expansion("non_existent_style")

    def test_render_character_svg(self):
        svg, dur = render_character_svg(self.yong_data, time=1.5, style="yan")
        self.assertGreater(dur, 3.0)
        self.assertIn("<svg", svg)
        self.assertIn("clipPath id=\"char_clip_0\"", svg)
        self.assertIn("stroke-width=\"181.48\"", svg)

    def test_render_scene_svg(self):
        svg, dur = render_scene_svg(self.poem_data, ["明", "月"], time=2.0, style="slender")
        self.assertGreater(dur, 2.0)
        self.assertIn("<svg", svg)
        self.assertIn("scene_mask_0_0", svg)

    def test_render_style_comparison_svg(self):
        svg, dur = render_style_comparison_svg(self.yong_data, time=2.0)
        self.assertGreater(dur, 3.0)
        self.assertIn("SLENDER KAI", svg)
        self.assertIn("STANDARD KAI", svg)
        self.assertIn("YAN KAI", svg)

    def test_create_animation_gif(self):
        def render_fn(t):
            return render_character_svg(self.yong_data, t)

        gif_bytes = create_animation_gif(render_fn, duration=0.8, fps=6)
        self.assertTrue(gif_bytes.startswith(b"GIF89a"))

    def test_create_vector_player(self):
        widget = create_vector_player(self.yong_data, style="yan")
        html_str = widget.data
        self.assertIn("callig_player_", html_str)
        self.assertIn("slider-seek", html_str)
        self.assertIn("YAN", html_str)

        multi_widget = create_vector_player(self.poem_data, char_list=["明", "月"])
        self.assertIn("明", multi_widget.data)

        comp_widget = create_vector_player(self.yong_data, styles=["slender", "standard", "yan"])
        self.assertIn("MULTI-STYLE", comp_widget.data)


if __name__ == "__main__":
    unittest.main()
