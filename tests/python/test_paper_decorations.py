"""Paper changes survive serialization and remain faint, stable background pixels."""
import unittest
import numpy as np
from backend.composition import scene_spec_from_params
from calligraphy.paper import render_writing_paper
from calligraphy.spec import Appearance


class PaperDecorationTests(unittest.TestCase):
    def test_motifs_roundtrip_are_distinct_faint_and_do_not_contaminate_cache(self):
        for palette in ('light', 'dark'):
            params = dict(palette=palette, paper_style='plain', stamp_enabled=False)
            base = scene_spec_from_params('永', 'kai', params).appearance
            baseline = np.array(render_writing_paper(480, 640, base))
            signatures = set()
            for motif in ('plum', 'orchid', 'bamboo', 'chrysanthemum'):
                appearance = scene_spec_from_params('永', 'kai', {**params, 'paper_decoration': motif}).appearance
                self.assertEqual(Appearance.from_dict(appearance.to_dict()), appearance)
                pixels = np.array(render_writing_paper(480, 640, appearance))
                signatures.add(pixels.tobytes())
                delta = np.abs(pixels.astype(int) - baseline.astype(int))
                self.assertGreater(delta.max(), 5)
                self.assertLess(delta.max(), 45)
                self.assertLess(np.any(delta, axis=2).mean(), .12)
                np.testing.assert_array_equal(pixels, render_writing_paper(480, 640, appearance))
                np.testing.assert_array_equal(baseline, render_writing_paper(480, 640, base))
            self.assertEqual(len(signatures), 4)

    def test_new_textures_are_distinct_on_both_palettes(self):
        for palette in ('light', 'dark'):
            signatures = set()
            for texture in ('fiber', 'laid', 'mottled', 'silver'):
                app = scene_spec_from_params('永', 'kai', dict(palette=palette, paper_style=texture, paper_tone='cool', stamp_enabled=False)).appearance
                paper = render_writing_paper(360, 480, app)
                self.assertEqual(paper.getpixel((0, 0)), app.paper_color)
                signatures.add(paper.tobytes())
            self.assertEqual(len(signatures), 4)

    def test_decoration_is_opt_in_and_appearance_hash_changes(self):
        default = scene_spec_from_params('永', 'kai', {})
        explicit = scene_spec_from_params('永', 'kai', {'paper_decoration': 'none', 'paper_tone': 'default'})
        self.assertEqual(default.spec_hash, explicit.spec_hash)
        for changes in ({'paper_decoration': 'plum'}, {'paper_tone': 'warm'}, {'paper_style': 'silver'}):
            self.assertNotEqual(default.spec_hash, scene_spec_from_params('永', 'kai', changes).spec_hash)
