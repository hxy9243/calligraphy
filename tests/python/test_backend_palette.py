"""Artwork palette is validated, durable and part of every render identity."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.composition import scene_spec_from_params
from backend.database import Database
from backend.editor_preview import cached_preview, editor_preview


class BackendPaletteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Database(f'sqlite:///{Path(self.temp.name) / "jobs.db"}')
        self.start_patch('backend.app.get_db', return_value=self.db)
        self.runner = self.start_patch('backend.app.get_runner').return_value
        self.editor = self.start_patch('backend.app.editor_preview', return_value=b'png')
        self.execute = self.start_patch('backend.app.execute_job')
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.client.cookies.set('calligraphy_session', 'palette-user')

    def start_patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_unsupported_palettes_are_rejected_before_preview_or_job_creation(self):
        for endpoint in ('/api/editor-preview', '/api/previews', '/api/renders'):
            for palette in ('sepia', 'Dark', '', None, 1, True, {'paper': '#141414'}):
                with self.subTest(endpoint=endpoint, palette=palette):
                    response = self.client.post(endpoint, json={'text': '永', 'palette': palette})
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.db.list_jobs('palette-user'), [])
        self.editor.assert_not_called()
        self.execute.assert_not_called()
        self.runner.notify.assert_not_called()

    def test_openapi_includes_palette_enum_and_legacy_light_default(self):
        schemas = self.client.get('/openapi.json').json()['components']['schemas']
        for name in ('EditorPreviewRequest', 'PreviewRequest', 'RenderRequest'):
            palette = schemas[name]['properties']['palette']
            self.assertEqual(palette['enum'], ['light', 'dark'])
            self.assertEqual(palette['default'], 'light')

    def test_editor_forwards_both_palettes_and_defaults_to_light(self):
        for palette in (None, 'light', 'dark'):
            payload = {'text': '永'}
            if palette is not None:
                payload['palette'] = palette
            response = self.client.post('/api/editor-preview', json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.editor.call_args.args[0]['palette'], palette or 'light')

    def test_render_identity_reuses_legacy_light_but_keeps_dark_separate_and_durable(self):
        old = self.db.create_job('old-light', 'palette-user', 'render', '永', 'kai',
                                 {'punctuation': 'omit'})
        ids = []
        for changes in ({}, {'palette': 'light'}, {'palette': 'dark'}, {'palette': 'dark'}):
            response = self.client.post('/api/renders', json={'text': '永', **changes})
            self.assertEqual(response.status_code, 202, response.text)
            ids.append(response.json()['job_id'])
        self.assertEqual(ids[:2], [old['job_id']] * 2)
        self.assertNotEqual(ids[0], ids[2])
        self.assertEqual(ids[2], ids[3])
        reopened = Database(self.db.db_url)
        self.assertEqual(reopened.get_job(ids[2])['params']['palette'], 'dark')
        self.assertNotIn('palette', reopened.get_job(old['job_id'])['params'])
        self.assertEqual(len(self.db.list_jobs('palette-user')), 2)

    def test_cached_editor_pixels_cannot_cross_palette_changes(self):
        cached_preview.cache_clear()
        self.addCleanup(cached_preview.cache_clear)

        def start_process(command, **kwargs):
            process = Mock(returncode=0)

            def communicate(payload, timeout):
                params = json.loads(payload)
                Path(command[-1]).write_bytes(params['palette'].encode())
                return b'', b''

            process.communicate.side_effect = communicate
            return process

        params = {'text': '永', 'style': 'kai'}
        with patch('backend.editor_preview.subprocess.Popen', side_effect=start_process) as process:
            for palette in ('light', 'dark', 'light', 'dark'):
                self.assertEqual(editor_preview({**params, 'palette': palette}), palette.encode())
            self.assertEqual(process.call_count, 2)
        self.assertEqual(cached_preview.cache_info().hits, 2)

    def test_legacy_and_explicit_light_preserve_colors_while_dark_resolves_both(self):
        defaults = scene_spec_from_params('永', 'kai', {})
        light = scene_spec_from_params('永', 'kai', {'palette': 'light'})
        self.assertEqual(defaults.appearance, light.appearance)
        self.assertEqual(defaults.appearance.paper_color, (248, 243, 233))
        self.assertEqual(defaults.appearance.ink_color, (28, 27, 24))
        self.assertEqual(defaults.spec_hash, light.spec_hash)
        for extra in ({}, {'palette': 'light'}):
            custom = scene_spec_from_params('永', 'kai', {
                'paper': '#f0e0d0', 'ink': '#123456', **extra,
            })
            self.assertEqual(custom.appearance.paper_color, (240, 224, 208))
            self.assertEqual(custom.appearance.ink_color, (18, 52, 86))
        dark = scene_spec_from_params('永', 'kai', {
            'palette': 'dark', 'paper': '#f0e0d0', 'ink': '#123456',
        })
        self.assertEqual(dark.appearance.paper_color, (20, 20, 20))
        self.assertEqual(dark.appearance.ink_color, (255, 255, 255))
        self.assertNotEqual(defaults.spec_hash, dark.spec_hash)


if __name__ == '__main__':
    unittest.main()
