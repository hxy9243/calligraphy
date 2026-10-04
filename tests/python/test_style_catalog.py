import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.style_catalog import STYLE_ALIASES, downloaded_catalog_entry
from backend.worker import _auto_prepare_font
from calligraphy.font_pipeline import load_bank, style_path
from calligraphy.renderer import create_scene
from calligraphy.spec import SceneSpec


ROOT = Path(__file__).resolve().parents[2]


class StyleCatalogTests(unittest.TestCase):
    def test_catalog_and_canonical_names_resolve_the_same_download(self):
        catalog = json.loads((ROOT / 'data/calligraphy_fonts.json').read_text())
        for catalog_id, style in STYLE_ALIASES.items():
            entry = next((item for item in catalog if item['id'] == catalog_id), None)
            if entry is None or entry.get('is_downloaded') != 1:
                continue
            with self.subTest(style=style):
                self.assertEqual(downloaded_catalog_entry(catalog, style), entry)
                self.assertEqual(downloaded_catalog_entry(catalog, catalog_id), entry)

    def test_only_downloaded_fonts_are_selected(self):
        unavailable = [{'id': 'longcang-xingshu', 'is_downloaded': 0}]
        self.assertIsNone(downloaded_catalog_entry(unavailable, 'longcang'))
        self.assertIsNone(downloaded_catalog_entry(unavailable, 'unknown'))

    def test_canonical_first_use_selects_the_correct_font(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'CALLIGRAPHY_STYLE_DIR': directory}):
            for style, filename in [('longcang', 'LongCang.ttf'), ('lishu hanwang', 'HanWangLiSuMedium.ttf')]:
                with self.subTest(style=style), \
                     patch('calligraphy.text.glyphs.resolve_glyphs', return_value={'永': {}}), \
                     patch('calligraphy.font_pipeline.prepare_style') as prepare:
                    _auto_prepare_font(style, '永')
                    prepare.assert_called_once()
                    self.assertEqual(prepare.call_args.args[0], style)
                    self.assertEqual(Path(prepare.call_args.kwargs['font_path']).name, filename)

    def test_first_use_prepares_and_renders_both_downloaded_fonts(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
                'CALLIGRAPHY_STYLE_DIR': str(Path(directory) / 'styles'),
                'CALLIGRAPHY_CONTACT_CACHE': str(Path(directory) / 'contacts.db')}):
            for style in ('longcang', 'lishu hanwang'):
                with self.subTest(style=style):
                    self.assertFalse(style_path(style).exists())
                    _auto_prepare_font(style, '永')
                    self.assertIn('永', load_bank(style)['glyphs'])
                    scene = create_scene(SceneSpec(text='永', style=style, layout={'width': 128, 'height': 128}))
                    self.assertEqual(scene.frame(scene.duration).size, (128, 128))
                    with patch('calligraphy.font_pipeline.prepare_style', side_effect=AssertionError('already registered')):
                        _auto_prepare_font(style, '永')


if __name__ == '__main__':
    unittest.main()
