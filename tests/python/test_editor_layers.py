"""Layered editor previews reuse text pixels for stamp-only edits."""
import base64
import io
import unittest
from unittest.mock import patch
from PIL import Image
from backend.app import EditorPreviewRequest, render_editor_preview
from backend.editor_preview import stamp_preview_layer
import json


class EditorLayerTests(unittest.TestCase):
    def test_stamp_changes_reuse_identical_stamp_free_render_payload(self):
        payloads = []
        with patch('backend.app.editor_preview', side_effect=lambda p: payloads.append(p) or b'png'):
            for col, row in [(0, .2), (2, .8)]:
                response = render_editor_preview(EditorPreviewRequest(
                    text='明月\n清泉', width=480, height=640, separate_stamp=True,
                    stamp_position='custom', stamp_col=col, stamp_row=row))
                body = json.loads(response.body)
                self.assertEqual(base64.b64decode(body['image']), b'png')
                seal = Image.open(io.BytesIO(base64.b64decode(body['stamp'])))
                self.assertEqual(seal.mode, 'RGBA')
                self.assertGreater(seal.size[0], 0)
        self.assertEqual(payloads[0], payloads[1])
        self.assertFalse(payloads[0]['stamp_enabled'])
        self.assertNotIn('stamp_col', payloads[0])
        self.assertNotIn('separate_stamp', payloads[0])

    def test_default_api_remains_png_and_retains_stamp_position(self):
        with patch('backend.app.editor_preview', return_value=b'png') as render:
            response = render_editor_preview(EditorPreviewRequest(text='永', stamp_position='custom', stamp_col=2))
        self.assertEqual(response.media_type, 'image/png')
        self.assertEqual(render.call_args.args[0]['stamp_col'], 2)

    def test_layer_respects_visibility_and_both_directions(self):
        params = dict(text='明月\n清泉', width=480, height=640, style='kai', font_size=48)
        for changes in [dict(stamp_enabled=False), dict(palette='dark'), dict(width=240)]:
            self.assertIsNone(stamp_preview_layer({**params, **changes}))
        for direction in ['vertical-rl', 'horizontal-lr']:
            self.assertTrue(stamp_preview_layer({**params, 'direction':direction}).startswith(b'\x89PNG'))
