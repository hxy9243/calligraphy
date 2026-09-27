import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
import numpy as np

from calligraphy.font_pipeline import prepare_style, load_bank, style_path, target_masks, validate_template
from calligraphy.contact_renderer import ContactScene, load_style


def make_font(path):
    builder = FontBuilder(1024, isTTF=True)
    builder.setupGlyphOrder(['.notdef', 'cross', 'line'])
    builder.setupCharacterMap({ord('十'): 'cross', ord('一'): 'line'})
    glyphs = {}
    for name in ['.notdef', 'cross', 'line']:
        pen = TTGlyphPen(None)
        rectangles = [] if name == '.notdef' else [(112, 430, 912, 530)]
        if name == 'cross': rectangles.append((460, 100, 560, 850))
        for x0, y0, x1, y1 in rectangles:
            pen.moveTo((x0, y0)); pen.lineTo((x1, y0)); pen.lineTo((x1, y1)); pen.lineTo((x0, y1)); pen.closePath()
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (1024, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=900, descent=-124)
    builder.setupNameTable({'familyName': 'Test Font', 'styleName': 'Regular'})
    builder.setupOS2(sTypoAscender=900, sTypoDescender=-124, usWinAscent=900, usWinDescent=124)
    builder.setupPost(); builder.setupMaxp(); builder.save(path)


CROSS = {'strokes': ['M 112 430 L 912 430 L 912 530 L 112 530 Z', 'M 460 100 L 560 100 L 560 850 L 460 850 Z'],
         'medians': [[[112, 480], [912, 480]], [[510, 850], [510, 100]]]}
LINE = {'strokes': CROSS['strokes'][:1], 'medians': CROSS['medians'][:1]}


class FontPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'CALLIGRAPHY_STYLE_DIR': str(self.root / 'styles')})
        self.env.start(); self.addCleanup(self.env.stop)
        self.font = self.root / 'test.ttf'; make_font(self.font)
        self.license = self.root / 'license.txt'; self.license.write_text('Synthetic test fixture created by this test.')

    def prepare(self, glyphs=None):
        return prepare_style('test font', glyphs or {'十': CROSS}, self.font, self.license, 'synthetic fixture')

    def test_font_to_bank_to_monotonic_replay_and_backward_seek(self):
        result = self.prepare()
        self.assertGreater(result['metrics']['十']['silhouette_iou'], .85)
        bank = load_bank('test-font')
        self.assertEqual(bank['font']['source'], 'synthetic fixture')
        self.assertEqual(load_style('test font'), bank['glyphs'])
        plan = {'schemaVersion': 1, 'width': 128, 'height': 128, 'duration': 1.2, 'strokeSeconds': .5,
                'schedule': [{'character': '十', 'strokeCount': 2, 'x': 0, 'y': 0, 'size': 128, 'start': .1, 'end': 1.1, 'duration': 1.0}]}
        scene = ContactScene(plan, bank['glyphs'])
        previous = np.asarray(scene.frame(0)).astype(int)
        partial = None
        for time in [.2, .4, .7, .9, 1.2]:
            current = np.asarray(scene.frame(time)).astype(int)
            # Lanczos resizing has negative lobes: inspect deposited coverage
            # separately, allowing small edge ringing in the RGB raster.
            self.assertLessEqual(int((current - previous).max()), 8)
            previous = current
            if time == .4: partial = current.copy()
        from calligraphy.contact_stroke import ContactStroke, complete_stroke
        for stroke in bank['glyphs']['十']:
            painter = ContactStroke(stroke); before = np.zeros((480, 480), np.float32)
            for progress in np.linspace(0, 1, 13):
                after = painter.advance(progress)
                self.assertTrue(np.all(after >= before)); before = after.copy()
            np.testing.assert_array_equal(before, complete_stroke(stroke))
        np.testing.assert_array_equal(partial, np.asarray(scene.frame(.4)))
        np.testing.assert_array_equal(ContactScene(plan, bank['glyphs']).frame(1.2), scene.frame(1.2))

    def test_extends_bank_without_changing_existing_geometry_and_is_offline_cached(self):
        self.prepare()
        before = copy.deepcopy(load_bank('test font')['glyphs']['十'])
        self.font.unlink()  # the managed font must survive removal of the original
        result = prepare_style('test font', {'一': LINE})
        self.assertEqual(result['prepared'], ['一'])
        self.assertEqual(load_bank('test font')['glyphs']['十'], before)
        with patch('calligraphy.font_pipeline.fit_glyph', side_effect=AssertionError('Should reuse geometry')):
            self.assertEqual(prepare_style('test font', {'一': LINE})['prepared'], [])

    def test_failed_batch_preserves_previous_bank(self):
        self.prepare()
        before = style_path('test font').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Missing font glyphs'):
            prepare_style('test font', {'一': LINE, '春': CROSS})
        self.assertEqual(before, style_path('test font').read_bytes())

    def test_changed_font_and_tampered_geometry_fail(self):
        self.prepare()
        owned_font = Path(load_bank('test font')['font']['path'])
        self.assertNotEqual(owned_font, self.font)
        owned_font.write_bytes(owned_font.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'font changed'):
            prepare_style('test font', {'一': LINE})
        path = style_path('test font'); bank = json.loads(path.read_text())
        bank['glyphs']['十'][0]['contacts'][0][0][0] += 1
        path.write_text(json.dumps(bank))
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            load_bank('test font')

    def test_disconnected_contact_segments_keep_both_pieces_without_a_bridge(self):
        from calligraphy.font_pipeline import fit_layer
        from calligraphy.contact_stroke import ContactStroke, complete_stroke
        layer = np.zeros((480,480), np.float32)
        layer[210:250,30:170] = 1; layer[210:250,310:450] = 1
        progress = np.broadcast_to(np.linspace(0,1,480), (480,480)).copy()
        stroke = fit_layer(layer, progress, 'disconnected test')
        self.assertEqual(len(stroke['segments']), 2)
        final = complete_stroke(stroke)
        self.assertGreater(final[220:240,40:160].mean(), .95)
        self.assertGreater(final[220:240,320:440].mean(), .95)
        self.assertEqual(final[:,190:290].sum(), 0)
        painter = ContactStroke(stroke); previous = np.zeros_like(final)
        for p in np.linspace(0,1,21):
            frame = painter.advance(p)
            self.assertTrue(np.all(frame >= previous)); previous = frame.copy()
            if p < .5: self.assertEqual(frame[:,310:].sum(), 0)
        np.testing.assert_array_equal(previous, final)

    def test_bad_style_names_templates_and_missing_font_characters_fail(self):
        for name in ['../outside', 'kai', 'lishu', '', 'UPPER']:
            with self.assertRaises(ValueError): style_path(name)
        for glyph in [None, {}, {'strokes': ['<svg/>'], 'medians': [[[0,0],[1,1]]]}, {'strokes': ['M 0 0 L 10 10'], 'medians': [[[0,0],[0,0]]]}]:
            with self.assertRaises(ValueError): validate_template(glyph)
        with self.assertRaisesRegex(ValueError, 'Missing font glyphs'):
            list(target_masks(self.font, ['春']))
        with self.assertRaisesRegex(ValueError, 'require --font and --license'):
            prepare_style('unregistered font', {'十': CROSS})


if __name__ == '__main__':
    unittest.main()
