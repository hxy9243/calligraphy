"""Preparation failures retain their actual cause through the worker and job API."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Database
from backend.worker import _auto_prepare_font, execute_job
from calligraphy.font_pipeline import FontBankNotFoundError, load_bank
from calligraphy.renderer import create_scene
from calligraphy.spec import SceneSpec


class FontPreparationErrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {'CALLIGRAPHY_STYLE_DIR': str(self.root / 'styles')})
        env.start()
        self.addCleanup(env.stop)

    def test_missing_bank_has_distinct_compatible_exception(self):
        with self.assertRaises(FontBankNotFoundError) as caught:
            load_bank('unregistered')
        self.assertIsInstance(caught.exception, ValueError)

    def test_first_scene_preparation_preserves_its_failure(self):
        cause = ValueError('Cannot fit 霜 stroke 7: degenerate stroke')
        with patch('calligraphy.renderer.resolve_glyphs', return_value={'霜': {}}), \
             patch('calligraphy.font_pipeline.prepare_style', side_effect=cause) as prepare:
            with self.assertRaisesRegex(ValueError, 'Cannot fit 霜 stroke 7'):
                create_scene(SceneSpec(text='霜', style='new-font'), font_path='font.ttf',
                             license_path='license.txt', fetch_missing=True)
        prepare.assert_called_once()

    def test_invalid_existing_bank_is_not_treated_as_missing(self):
        with patch('calligraphy.renderer.load_bank', side_effect=ValueError('Font bank geometry checksum mismatch')), \
             patch('calligraphy.font_pipeline.prepare_style') as prepare:
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                create_scene(SceneSpec(text='霜', style='existing-font'), font_path='font.ttf', fetch_missing=True)
        prepare.assert_not_called()

    def test_worker_and_job_api_report_original_preparation_error(self):
        # Use tracked text files as path fixtures: prepare_style is deliberately
        # fault-injected, so this test needs no private font or font fitting.
        entry = {'file_path': 'README.md', 'license_path': 'ARPHICPL.TXT'}
        cause = 'Cannot fit 霜 stroke 7: Cannot infer ordered guide for degenerate stroke'
        db = Database(f'sqlite:///{self.root / "jobs.db"}')
        job = db.create_job('test-font-error', 'font-error-owner', 'video', '霜', 'test-font', {})
        with patch('backend.worker.downloaded_catalog_entry', return_value=entry), \
             patch('calligraphy.text.glyphs.resolve_glyphs', return_value={'霜': {}}), \
             patch('calligraphy.font_pipeline.prepare_style', side_effect=ValueError(cause)), \
             patch('backend.worker.create_scene') as scene:
            self.assertFalse(execute_job(job, db))
        scene.assert_not_called()
        saved = db.get_job(job['job_id'])
        self.assertEqual(saved['status'], 'failed')
        self.assertIn(cause, saved['error_message'])
        self.assertNotIn('Unknown contact style', saved['error_message'])
        self.assertNotIn('prepare:font', saved['error_message'])
        with patch('backend.app.get_db', return_value=db), TestClient(app) as client:
            client.cookies.set('calligraphy_session', 'font-error-owner')
            response = client.get('/api/jobs/test-font-error')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['error_message'], saved['error_message'])


if __name__ == '__main__':
    unittest.main()
