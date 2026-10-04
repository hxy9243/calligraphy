import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fontTools.ttLib import TTFont
from backend.app import app
from backend.database import Database
from backend.style_catalog import STYLE_ALIASES
from backend.worker import _auto_prepare_font

ROOT = Path(__file__).resolve().parents[2]

class PoetryFontsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = Database(f"sqlite:///{Path(self.directory.name) / 'test.db'}")
        database_patch = patch('backend.app.get_db', return_value=database)
        database_patch.start()
        self.addCleanup(database_patch.stop)

    def test_bundled_fonts_coverage_license_and_fresh_style_menu(self):
        fonts = json.loads((ROOT / 'data/poetry-fonts.json').read_text())
        with patch('backend.app.registered_styles', return_value=[]):
            client = TestClient(app)
            styles = {s['id'] for s in client.get('/api/styles').json()['styles']}
        for font in fonts:
            with self.subTest(font=font['id']):
                self.assertIn(STYLE_ALIASES.get(font['id'], font['id']), styles)
                self.assertEqual(font['coverage']['missing'], '')
                self.assertEqual(font['coverage']['unique_traditional_characters'], 250)
                self.assertTrue((ROOT / font['license_file']).read_text().strip())
                face = TTFont(ROOT / font['file'])
                self.assertEqual(face['name'].getDebugName(1), font['family'])
                response = client.get('/fonts/' + Path(font['file']).name)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.content), (ROOT / font['file']).stat().st_size)

    def test_first_preparation_keeps_each_fonts_own_license(self):
        fonts = json.loads((ROOT / 'data/poetry-fonts.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            for font in fonts:
                style = STYLE_ALIASES.get(font['id'], font['id'])
                with self.subTest(style=style), patch('calligraphy.font_pipeline.style_path', return_value=Path(directory) / 'absent.json'), patch('calligraphy.text.glyphs.resolve_glyphs', return_value={'永': {}}), patch('calligraphy.font_pipeline.prepare_style') as prepare:
                    _auto_prepare_font(style, '永')
                    self.assertEqual(prepare.call_args.kwargs['license_path'], str(ROOT / font['license_file']))
                    self.assertEqual(prepare.call_args.kwargs['font_path'], str(ROOT / font['file']))
