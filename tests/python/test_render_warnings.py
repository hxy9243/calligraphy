"""Successful approximate renders keep an owner-visible, persisted caveat."""
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import Database
from backend.worker import execute_job
from calligraphy.font_pipeline import prepare_style, style_path
from calligraphy.renderer import create_scene
from calligraphy.spec import SceneSpec
from test_font_pipeline import CROSS, make_font

WARNING = '部分細小筆畫使用推估筆路；請檢視成品。'


class RenderWarningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(os.environ, {
            'CALLIGRAPHY_STYLE_DIR': str(self.root / 'styles'),
            'CALLIGRAPHY_CONTACT_CACHE': str(self.root / 'contacts.db'),
            'CALLIGRAPHY_OUTPUT_DIR': str(self.root / 'outputs'),
        })
        env.start(); self.addCleanup(env.stop)
        font = self.root / 'fixture.ttf'; make_font(font)
        license = self.root / 'license.txt'; license.write_text('Synthetic fixture')
        prepare_style('fixture', {'十': CROSS}, font, license, workers=1)
        self.url = f'sqlite:///{self.root / "jobs.db"}'
        self.db = Database(self.url)
        db_patch = patch('backend.database._DB_INSTANCE', self.db)
        db_patch.start(); self.addCleanup(db_patch.stop)
        self.client = TestClient(app); self.addCleanup(self.client.close)
        self.client.get('/api/styles')
        self.owner = self.client.cookies['calligraphy_session']

    def mark_fallback(self, character='十'):
        path = style_path('fixture')
        bank = json.loads(path.read_text())
        bank['metrics'].setdefault(character, {})['guide_fallback_strokes'] = [1]
        path.write_text(json.dumps(bank))

    def job(self, name):
        return self.db.create_job(name, self.owner, 'preview', '十', 'fixture',
            {'format': 'png', 'width': 96, 'height': 96, 'font_size': 32})

    def test_warning_only_for_requested_fallback_glyph_and_warm_bank(self):
        spec = SceneSpec(text='十', style='fixture', layout={'width': 96, 'height': 96})
        self.assertIsNone(getattr(create_scene(spec), 'render_warning', None))
        self.mark_fallback('永')
        self.assertIsNone(getattr(create_scene(spec), 'render_warning', None))
        self.mark_fallback()
        for _ in range(2):
            with patch('calligraphy.font_pipeline.prepare_style', side_effect=AssertionError('must reuse existing bank')):
                self.assertEqual(create_scene(spec).render_warning, WARNING)

    def test_success_warning_persists_on_worker_result_api_and_restart(self):
        self.mark_fallback()
        for name in ('first', 'warm'):
            self.assertTrue(execute_job(self.job(name), self.db))
            row = self.db.get_job(name)
            self.assertEqual(row['status'], 'succeeded')
            self.assertIsNone(row['error_message'])
            self.assertEqual(row['warning_message'], WARNING)
            self.assertEqual(self.client.get(f'/api/jobs/{name}').json()['warning_message'], WARNING)
        rows = self.client.get('/api/jobs').json()['jobs']
        self.assertEqual([row['warning_message'] for row in rows], [WARNING, WARNING])
        reopened = Database(self.url)
        self.assertEqual(reopened.get_job('warm')['warning_message'], WARNING)
        with TestClient(app) as stranger:
            self.assertEqual(stranger.get('/api/jobs/warm').status_code, 404)
            self.assertEqual(stranger.get('/api/jobs').json()['jobs'], [])

    def test_still_export_response_includes_success_caveat(self):
        self.mark_fallback()
        with patch('backend.app.checked_style', return_value='fixture'), \
             patch('backend.app.execute_job', side_effect=execute_job):
            response = self.client.post('/api/previews', json={
                'text': '十', 'style': 'fixture', 'width': 96, 'height': 96, 'format': 'png'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['warning_message'], WARNING)
        self.assertTrue(response.json()['preview_url'])

    def test_normal_success_has_no_warning(self):
        self.assertTrue(execute_job(self.job('normal'), self.db))
        self.assertIsNone(self.client.get('/api/jobs/normal').json()['warning_message'])

    def test_additive_migration_preserves_legacy_jobs_and_is_idempotent(self):
        self.job('legacy')
        with self.db._get_sqlite_conn() as conn:
            conn.execute('ALTER TABLE jobs DROP COLUMN warning_message')
        with ThreadPoolExecutor(max_workers=3) as pool:
            migrated = list(pool.map(lambda _: Database(self.url), range(3)))
        for db in migrated:
            row = db.get_job('legacy')
            self.assertEqual(row['text'], '十')
            self.assertIsNone(row['warning_message'])
        migrated[0].update_job('legacy', warning_message=WARNING)
        self.assertEqual(migrated[-1].get_job('legacy')['warning_message'], WARNING)


if __name__ == '__main__':
    unittest.main()
