"""Real page pixels and decoded frames keep the editor's logical composition."""
import io
import json
import math
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from backend.app import app
from backend.composition import scene_spec_from_params
from backend.database import Database
from backend.editor_preview import editor_preview, render_pixels
from backend.worker import execute_job
from calligraphy.font_pipeline import prepare_style
from calligraphy.renderer import create_scene
from calligraphy.spec import RenderPlan
from test_font_pipeline import CROSS, make_font


class StudioCompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.env = patch.dict(os.environ, {
            'CALLIGRAPHY_KAI_CACHE': str(cls.root / 'kai.db'),
            'CALLIGRAPHY_CONTACT_CACHE': str(cls.root / 'contact.db'),
            'CALLIGRAPHY_STYLE_DIR': str(cls.root / 'styles'),
            'CALLIGRAPHY_OUTPUT_DIR': str(cls.root / 'outputs'),
            'CALLIGRAPHY_PREVIEW_WORKERS': '1',
        })
        cls.env.start()
        font = cls.root / 'data/fonts/fixture.ttf'
        font.parent.mkdir(parents=True)
        make_font(font)
        license = cls.root / 'license.txt'
        license.write_text('Synthetic fixture')
        prepare_style('fixture', {'十': CROSS}, font, license, workers=1)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.db = Database(f'sqlite:///{self.root / (self.id().split(".")[-1] + ".db")}')
        self.start_patch('backend.app.get_db', return_value=self.db)
        self.start_patch('backend.app.get_runner')
        self.start_patch('backend.worker._auto_prepare_font')
        self.start_patch('backend.editor_preview.ROOT', self.root)
        self.start_patch('backend.editor_preview.private_catalog', return_value=[{
            'id': 'fixture', 'is_downloaded': 1, 'file_path': 'data/fonts/fixture.ttf',
        }])
        # Supply hermetic geometry, not a mock scene: fitting, page planning,
        # rasterization, SVG and FFmpeg encoding run through production code.
        self.start_patch('calligraphy.renderer.create_scene', side_effect=self.create_scene)
        self.start_patch('backend.worker.create_scene', side_effect=self.create_scene)
        self.start_patch('backend.app.editor_preview', side_effect=render_pixels)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.client.cookies.set('calligraphy_session', self.id())

    def start_patch(self, *args, **kwargs):
        p = patch(*args, **kwargs)
        self.addCleanup(p.stop)
        return p.start()

    def create_scene(self, spec, **kwargs):
        return create_scene(spec, glyphs={'十': CROSS}, fetch_missing=False, glyph_workers=1)

    def params(self, **overrides):
        return dict(text='十十\n十', style='kai', width=240, height=320,
                    font_size=68, spacing=.25, fit=True, direction='vertical-rl',
                    punctuation='omit', **overrides)

    def submit(self, endpoint, params):
        response = self.client.post(endpoint, json=params)
        self.assertIn(response.status_code, (200, 202), response.text)
        return response

    def still(self, params):
        response = self.submit('/api/previews', {**params, 'format': 'png'})
        job = self.db.get_job(response.json()['job_id'])
        self.assertEqual(job['status'], 'succeeded')
        return Image.open(job['output_path']).convert('RGB'), job

    def test_kai_editor_pixels_equal_downsampled_exports_in_both_directions(self):
        for index, (width, height, direction, size, fit) in enumerate([
            (240, 320, 'vertical-rl', 68, True),
            (720, 960, 'vertical-rl', 110, False),
            (1280, 720, 'horizontal-lr', 48, True),
            (640, 2200, 'vertical-rl', 140, False),
            (2400, 1280, 'horizontal-lr', 160, True),
        ]):
            with self.subTest(direction=direction, size=size, fit=fit):
                self.client.cookies.set('calligraphy_session', f'pixels-{index}')
                params = {**self.params(), 'width': width, 'height': height,
                          'direction': direction, 'font_size': size, 'fit': fit}
                preview = Image.open(io.BytesIO(self.submit('/api/editor-preview', params).content)).convert('RGB')
                still, job = self.still(params)
                self.assertEqual(still.size, (width, height))
                self.assertEqual(job['params']['font_size'], size)
                self.assertEqual(job['params']['fit'], fit)
                still.thumbnail((640, 640), Image.Resampling.LANCZOS)
                self.assertEqual(preview.size, still.size)
                np.testing.assert_array_equal(preview, still)
                self.assertTrue((np.asarray(preview)[:, :, 0] < 120).any())

    def test_font_preview_uses_export_cell_positions_scale_and_ink_without_fitting(self):
        for direction in ('vertical-rl', 'horizontal-lr'):
            params = {**self.params(), 'style': 'fixture', 'direction': direction}
            with patch('calligraphy.font_pipeline.prepare_style', side_effect=AssertionError('editor must not fit')):
                preview = Image.open(io.BytesIO(render_pixels(params))).convert('RGB')
            still, _ = self.still(params)
            self.assertEqual(preview.size, still.size)
            a, b = np.asarray(preview), np.asarray(still)
            np.testing.assert_array_equal(a[0, 0], b[0, 0])
            self.assertTrue(np.any(np.all(a == [28, 27, 24], axis=2)))
            ink_a, ink_b = a[:, :, 0] < 128, b[:, :, 0] < 128
            # Contact fitting can change stroke edges; cell geometry and the
            # source silhouette's normalization/ink must not jump between paths.
            self.assertGreater((ink_a & ink_b).sum() / (ink_a | ink_b).sum(), .85)
            for ink in (ink_a, ink_b):
                self.assertTrue(ink.any())
            np.testing.assert_allclose(np.argwhere(ink_a).mean(axis=0),
                                       np.argwhere(ink_b).mean(axis=0), atol=1)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg is required for decoded-frame integration')
    def test_video_dimensions_partial_and_final_frames_match_still_scene(self):
        params = {**self.params(), 'text': '十十', 'width': 240, 'height': 160,
                  'direction': 'horizontal-lr', 'font_size': 72, 'fit': False,
                  'fps': 4, 'speed': 1}
        still, _ = self.still(params)
        response = self.submit('/api/renders', params)
        job = self.db.get_job(response.json()['job_id'])
        self.assertTrue(execute_job(job, self.db))
        job = self.db.get_job(job['job_id'])
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', job['output_path'],
            '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', '-'])
        frames = np.frombuffer(raw, dtype=np.uint8).reshape((-1, 160, 240, 3))
        scene = self.create_scene(scene_spec_from_params(params['text'], params['style'], params))
        self.assertEqual(len(frames), math.ceil(scene.duration * params['fps']))
        for index in (3, 5, len(frames) - 1):
            time = scene.duration if index == len(frames) - 1 else index / params['fps']
            expected = np.asarray(scene.frame(time))
            self.assertLess(np.abs(frames[index].astype(float) - expected).mean(), 2.0)
            mask_a, mask_b = frames[index, :, :, 0] < 128, expected[:, :, 0] < 128
            self.assertGreater((mask_a & mask_b).sum() / (mask_a | mask_b).sum(), .90)
        np.testing.assert_array_equal(scene.frame(scene.duration), still)
        self.assertLess((frames[3, :, :, 0] < 128).sum(), (frames[-1, :, :, 0] < 128).sum())

    def test_size_and_fit_change_layout_without_changing_explicit_line_wrapping(self):
        params = {**self.params(), 'text': '十十十', 'width': 160, 'height': 240,
                  'direction': 'horizontal-lr', 'font_size': 140}
        plan = RenderPlan.create(scene_spec_from_params('十十十', 'kai', params), {'十': 2})
        self.assertEqual({p['row'] for p in plan.schedule}, {0})
        self.assertLess(plan.schedule[0]['size'], 140)
        preview = Image.open(io.BytesIO(render_pixels(params)))
        still, _ = self.still(params)
        np.testing.assert_array_equal(preview, still)
        response = self.client.post('/api/editor-preview', json={**params, 'fit': False})
        self.assertEqual(response.status_code, 422)
        self.assertIn('enable fit', response.text)
        small = {**params, 'font_size': 24, 'fit': False}
        small_plan = RenderPlan.create(scene_spec_from_params('十十十', 'kai', small), {'十': 2})
        self.assertEqual(small_plan.schedule[0]['size'], 24)
        self.assertFalse(np.array_equal(preview, Image.open(io.BytesIO(render_pixels(small)))))

    def test_validation_bounds_and_video_evenness_before_jobs(self):
        for endpoint in ('/api/editor-preview', '/api/previews', '/api/renders'):
            for override in ({'width': 2401}, {'height': 63}, {'width': 2400, 'height': 2400},
                             {'font_size': 7}, {'font_size': 161}):
                with self.subTest(endpoint=endpoint, override=override):
                    response = self.client.post(endpoint, json={**self.params(), **override})
                    self.assertIn(response.status_code, (400, 422), response.text)
        response = self.client.post('/api/renders', json={**self.params(), 'width': 721})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.db.list_jobs(self.id()), [])

    def test_legacy_defaults_preserve_page_fit_and_deduplication(self):
        old = self.db.enqueue_render('legacy', 'legacy-user', '十十', 'kai', {'punctuation': 'omit'})
        self.client.cookies.set('calligraphy_session', 'legacy-user')
        response = self.submit('/api/renders', {'text': '十十', 'style': 'kai'})
        self.assertEqual(response.json()['job_id'], old['job_id'])
        spec = scene_spec_from_params('十十', 'kai', old['params'])
        plan = RenderPlan.create(spec, {'十': 2})
        self.assertEqual((plan.width, plan.height), (720, 960))
        self.assertGreater(plan.schedule[0]['size'], 160)
        previous = {'width': 720, 'height': 960, 'direction': 'vertical-rl',
                    'characters_per_line': None, 'gap': .18}
        spec.layout = previous
        self.assertEqual(plan.schedule, RenderPlan.create(spec, {'十': 2}).schedule)

    def test_render_identity_and_editor_cache_include_every_composition_field(self):
        params = self.params()
        first = self.submit('/api/renders', params).json()['job_id']
        repeated = self.submit('/api/renders', dict(reversed(list(params.items())))).json()['job_id']
        self.assertEqual(first, repeated)
        for index, changes in enumerate([{'font_size': 69}, {'fit': False}, {'width': 320}, {'height': 400}]):
            # Direct DB identity avoids the intentional three-submission budget.
            old = self.db.get_job(first)
            modified = self.db.enqueue_render(f'variant-{index}', old['session_id'], old['text'], old['style'],
                                             {**old['params'], **changes})
            self.assertNotEqual(modified['job_id'], first)
        payloads = []
        with patch('backend.editor_preview.cached_preview', side_effect=lambda p: payloads.append(p) or b'png'):
            for changes in ({}, {'font_size': 69}, {'fit': False}, {'width': 320}, {'height': 400}):
                editor_preview({**params, **changes})
        self.assertEqual(len(set(payloads)), 5)
        self.assertEqual(json.loads(payloads[0])['width'], 240)
