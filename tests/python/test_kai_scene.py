import json
import base64
import io
import re
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from calligraphy.kai_scene import KaiScene, prepare_kai
from calligraphy.renderer import create_scene, TemplateScene
from calligraphy.spec import SceneSpec, Appearance, Transforms
from calligraphy.text.glyphs import resolve_glyphs


class KaiSceneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = str(Path(self.temp.name) / 'geometry.db')
        env = patch.dict(os.environ, {'CALLIGRAPHY_KAI_CACHE': self.cache})
        env.start()
        self.addCleanup(env.stop)

    def test_default_cache_replay_and_explicit_legacy_mode(self):
        spec = SceneSpec(text='永永', layout={'width': 128, 'height': 192})
        scene = create_scene(spec)
        self.assertIsInstance(scene, KaiScene)
        self.assertEqual(set(scene.programs), {'永'})
        smoothing = scene.programs['永']['provenance']['crossingSmoothing']
        self.assertEqual(smoothing['method'], 'crossing-rails-kai/1')
        self.assertEqual(len(smoothing['strokes']), len(scene.programs['永']['strokes']))
        self.assertEqual(scene.programs['永']['provenance']['engine']['engine_version'], 'kai-fitted-v1')
        with patch('calligraphy.kai_scene.fit_contact_stroke', side_effect=AssertionError('cache miss')):
            cached = create_scene(spec)
        t = scene.plan['schedule'][0]['start'] + .1
        partial = np.asarray(scene.frame(t))
        scene.frame(scene.duration)
        np.testing.assert_array_equal(scene.frame(t), partial)
        np.testing.assert_array_equal(scene.frame(scene.duration), cached.frame(cached.duration))
        self.assertIn('data-engine="kai-fitted"', scene.frame_svg(scene.duration))
        self.assertIsInstance(create_scene(spec, mode='template'), TemplateScene)

    def test_concurrent_preparation_reuses_one_program(self):
        glyphs = resolve_glyphs('永')
        from calligraphy.stroke_fitting import fit_contact_stroke
        with patch('calligraphy.kai_scene.fit_contact_stroke', wraps=fit_contact_stroke) as fitter:
            with ThreadPoolExecutor(max_workers=2) as executor:
                a = executor.submit(prepare_kai, glyphs, self.cache)
                b = executor.submit(prepare_kai, glyphs, self.cache)
                self.assertEqual(a.result(), b.result())
        self.assertEqual(fitter.call_count, len(glyphs['永']['strokes']))
        from calligraphy.artifact_cache import ArtifactCache
        self.assertEqual(len(ArtifactCache(self.cache).list_versions()), 1)

    def test_reject_failed_fit_without_caching(self):
        glyphs = resolve_glyphs('永')
        with patch('calligraphy.kai_scene.fit_contact_stroke', return_value={'report': {'targetReached': False}}):
            with self.assertRaisesRegex(ValueError, 'failed shape/motion'):
                prepare_kai(glyphs, self.cache)
        from calligraphy.artifact_cache import ArtifactCache
        self.assertEqual(ArtifactCache(self.cache).list_versions(), [])

    def test_changed_guide_gets_a_new_cache_version(self):
        glyphs = resolve_glyphs('永')
        prepare_kai(glyphs, self.cache)
        altered = json.loads(json.dumps(glyphs))
        altered['永']['medians'][0][0][0] += 1
        with patch('calligraphy.kai_scene.fit_contact_stroke', side_effect=ValueError('different guide')):
            with self.assertRaisesRegex(ValueError, 'different guide'):
                prepare_kai(altered, self.cache)

    def test_custom_appearance_transforms_and_svg_match_pixels(self):
        spec = SceneSpec(text='永', layout={'width': 192, 'height': 192},
                         appearance=Appearance((230, 210, 190), (40, 60, 80)),
                         transforms=Transforms(scale=.8, stretch=1.1, rotation=5))
        scene = create_scene(spec)
        frame = scene.frame(scene.duration)
        self.assertEqual(frame.getpixel((0, 0)), spec.appearance.paper_color)
        entry = scene.plan['schedule'][0]
        mask = scene.glyph_mask('永')
        from PIL import Image
        size = entry['size']
        alpha = Image.fromarray(np.uint8(mask * 255)).resize(
            (round(size*.92*.8*1.1), round(size*.92*.8)), Image.Resampling.LANCZOS)
        patch_image = Image.new('RGBA', alpha.size, spec.appearance.ink_color + (0,))
        patch_image.putalpha(alpha)
        patch_image = patch_image.rotate(-5, resample=Image.Resampling.BICUBIC, expand=True)
        expected = Image.new('RGB', frame.size, spec.appearance.paper_color)
        expected.paste(patch_image, (round(entry['x']+size/2-patch_image.width/2),
                                    round(entry['y']+size/2-patch_image.height/2)), patch_image)
        np.testing.assert_array_equal(frame, expected)
        payload = re.search(r'base64,([^" ]+)', scene.frame_svg(scene.duration)).group(1)
        with Image.open(io.BytesIO(base64.b64decode(payload))) as embedded:
            np.testing.assert_array_equal(frame, embedded)

    def test_video_timing_finishes_last_stroke_and_disables_parallel_frames(self):
        from calligraphy.renderer import export_video
        from calligraphy.contact_stroke import ContactStroke
        from unittest.mock import Mock
        spec = SceneSpec(text='永', layout={'width':128,'height':128},
                         timing={'intro':0,'outro':0,'stroke_seconds':.2})
        scene = create_scene(spec)
        expected_last = scene.frame(scene.duration).tobytes()
        entry = scene.plan['schedule'][0]
        scene._active = None
        half = scene._partial(0, entry, .1)
        expected_half = ContactStroke(scene.glyphs['永'][0]).advance(.5)
        np.testing.assert_array_equal(half, expected_half)
        encoder = Mock()
        encoder.wait.return_value = 0
        with patch('calligraphy.renderer.subprocess.Popen', return_value=encoder), \
             patch('concurrent.futures.ThreadPoolExecutor', side_effect=AssertionError('parallel Kai')), \
             patch.object(scene, 'frame', wraps=scene.frame) as render:
            count = export_video(scene, Path(self.temp.name)/'video.mp4', fps=4, workers=8)
        self.assertEqual(count,4)
        self.assertEqual([call.args[0] for call in render.call_args_list], [0,.25,.5,1])
        self.assertEqual(encoder.stdin.write.call_args_list[-1].args[0], expected_last)
