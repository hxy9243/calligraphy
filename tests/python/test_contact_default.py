import base64
import copy
import io
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
from calligraphy.contact_preparation import prepare_contacts
from calligraphy.renderer import create_scene, export_video, TemplateScene
from calligraphy.spec import SceneSpec, Appearance, Transforms
from calligraphy.styled_contact_scene import StyledContactScene
from calligraphy.font_pipeline import prepare_style, load_bank, style_path
from test_font_pipeline import make_font, CROSS


class ContactDefaultTests(unittest.TestCase):
    def test_registered_default_cache_exports_and_source_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'CALLIGRAPHY_STYLE_DIR': str(root / 'styles'),
                                        'CALLIGRAPHY_CONTACT_CACHE': str(root / 'cache.db')}):
                font = root / 'test.ttf'; make_font(font)
                license = root / 'license.txt'; license.write_text('Synthetic fixture')
                prepare_style('fixture', {'十': CROSS}, font, license, 'test fixture')
                original = style_path('fixture').read_bytes()
                spec = SceneSpec(text='十', style='fixture', layout={'width': 128, 'height': 128},
                                 appearance=Appearance(ink_color=(50, 60, 70), paper_color=(240, 230, 220)),
                                 transforms=Transforms(rotation=3, stretch=1.1))
                with patch('calligraphy.renderer.LayerStore', side_effect=AssertionError('legacy renderer')):
                    scene = create_scene(spec)
                self.assertIsInstance(scene, StyledContactScene)
                self.assertIn('十', scene.smoothing_reports)
                time = scene.plan['schedule'][0]['start'] + .1
                partial = np.asarray(scene.frame(time))
                scene.frame(scene.duration)
                np.testing.assert_array_equal(partial, scene.frame(time))
                svg = scene.frame_svg(scene.duration)
                embedded = Image.open(io.BytesIO(base64.b64decode(re.search('base64,([^\"]+)', svg)[1])))
                np.testing.assert_array_equal(embedded, scene.frame(scene.duration))
                self.assertIn('data-engine="smoothed-contact"', svg)
                with patch('calligraphy.contact_preparation.smooth_kai_contacts', side_effect=AssertionError('cache miss')):
                    create_scene(spec)
                self.assertEqual(original, style_path('fixture').read_bytes())
                export_video(scene, root / 'clip.mp4', fps=2, speed=10)
                self.assertGreater((root / 'clip.mp4').stat().st_size, 100)
                glyphs = load_bank('fixture')['glyphs']
                from calligraphy.stroke_crossings import smooth_kai_contacts
                with patch('calligraphy.contact_preparation.smooth_kai_contacts', wraps=smooth_kai_contacts) as repair:
                    prepare_contacts(glyphs, source={'font': 'other'})
                    self.assertEqual(repair.call_count, 1)
                    prepare_contacts(glyphs, source={'font': 'other'})
                    self.assertEqual(repair.call_count, 1)
                    changed = copy.deepcopy(glyphs)
                    changed['十'][0]['tension'] = .45
                    prepare_contacts(changed, source={'font': 'other'})
                    self.assertEqual(repair.call_count, 2)

    def test_yan_default_fits_expanded_geometry(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'CALLIGRAPHY_KAI_CACHE': directory + '/kai.db'}):
            scene = create_scene(SceneSpec(text='十', style='yan'), glyphs={'十': CROSS})
            self.assertIsInstance(scene, StyledContactScene)
            self.assertEqual(scene.programs['十']['provenance']['outline_expansion'], 16.48)
            self.assertIsInstance(create_scene(SceneSpec(text='十', style='yan'), glyphs={'十': CROSS}, mode='template'), TemplateScene)
