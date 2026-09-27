import copy
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from calligraphy.brush_grammar import complete
from calligraphy.contact_renderer import ContactScene, export_png, export_video, load_style, style_manifest


def plan(glyphs, text='人人', width=240, height=120):
    step = .2
    schedule = []
    cursor = .1
    for i, character in enumerate(text):
        count = len(glyphs[character])
        duration = count * step
        schedule.append(dict(character=character, index=i, x=i*100+10, y=10, size=100,
            strokeCount=count, start=cursor, end=cursor+duration, duration=duration))
        cursor += duration + .1
    return dict(schemaVersion=1, width=width, height=height, strokeSeconds=step, duration=cursor+.2, schedule=schedule)


class ContactRendererTests(unittest.TestCase):
    def setUp(self):
        self.glyphs = load_style('lishu')
        self.plan = plan(self.glyphs)

    def test_promoted_collections_have_verified_provenance_and_matching_coverage(self):
        manifest = style_manifest()
        self.assertEqual(set(manifest['styles']), {'lishu', 'liu', 'yan-contact'})
        for style, metadata in manifest['styles'].items():
            raw = files('calligraphy').joinpath('assets/contact', metadata['file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata['sha256'])
            glyphs = load_style(style)
            self.assertEqual(len(glyphs), 25)
            self.assertEqual(sum(map(len, glyphs.values())), 237)
            self.assertEqual(set(glyphs), set(self.glyphs))
        with self.assertRaisesRegex(ValueError, 'Unknown contact style'):
            load_style('wang')

    def test_final_glyphs_equal_original_contact_deposition_for_every_style(self):
        for style in style_manifest()['styles']:
            glyphs = load_style(style)
            scene = ContactScene(plan(glyphs), glyphs)
            for character in ['人', '月', '長']:
                expected = np.maximum.reduce([complete(s) for s in glyphs[character]])
                np.testing.assert_array_equal(scene.glyph_mask(character), expected)

    def test_frames_support_backward_seeking_repetitions_and_exact_completion(self):
        scene = ContactScene(self.plan, self.glyphs)
        previous = np.zeros((120, 240), bool)
        for time in np.linspace(0, self.plan['duration'], 15):
            frame = np.asarray(scene.frame(float(time)))
            ink = frame[:, :, 0] < 150
            self.assertTrue(np.all(ink | ~previous))
            previous = ink
        expected = ContactScene(self.plan, self.glyphs).frame(self.plan['duration'])
        self.assertEqual(scene.frame(self.plan['duration']).tobytes(), expected.tobytes())
        self.assertEqual(scene.frame(.25).tobytes(), ContactScene(self.plan, self.glyphs).frame(.25).tobytes())
        self.assertEqual(scene.frame(self.plan['duration']).tobytes(), expected.tobytes())
        self.assertTrue(previous[:, :120].any() and previous[:, 120:].any())

    def test_future_glyph_does_not_appear_and_input_mutation_cannot_change_scene(self):
        scene = ContactScene(self.plan, self.glyphs)
        snapshot = scene.frame(.3).tobytes()
        self.plan['schedule'][0]['x'] = 50
        self.glyphs['人'][0]['contacts'][0][0][0] = -10000
        self.assertEqual(scene.frame(.3).tobytes(), snapshot)
        frame = np.asarray(scene.frame(.3))
        self.assertTrue(np.all(frame[:, 120:, 0] == 249))

    def test_invalid_plan_and_missing_characters_are_rejected(self):
        for field, value in [('width', 0), ('width', 101.5), ('strokeSeconds', float('nan')), ('schemaVersion', 2), ('schedule', [1])]:
            p = copy.deepcopy(self.plan); p[field] = value
            with self.assertRaises(ValueError): ContactScene(p, self.glyphs)
        for field, value in [('strokeCount', 99), ('character', '天'), ('size', 2000), ('end', -1), ('start', -.2)]:
            p = copy.deepcopy(self.plan); p['schedule'][0][field] = value
            with self.assertRaises(ValueError): ContactScene(p, self.glyphs)
        with self.assertRaises(ValueError): ContactScene(self.plan, self.glyphs).frame(float('nan'))

    def test_png_export_has_requested_dimensions(self):
        scene = ContactScene(self.plan, self.glyphs)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'page.png'
            export_png(scene, output)
            from PIL import Image
            with Image.open(output) as image:
                self.assertEqual(image.size, (240, 120))
                self.assertEqual(image.tobytes(), scene.frame(self.plan['duration']).tobytes())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg/FFprobe required')
    def test_video_and_encoder_failures(self):
        import subprocess
        scene = ContactScene(self.plan, self.glyphs)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'page.mp4'
            count = export_video(scene, output, fps=2, speed=1)
            metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height,nb_frames', '-of', 'json', str(output)]))['streams'][0]
            self.assertEqual((metadata['width'], metadata['height'], int(metadata['nb_frames'])), (240, 120, count))
            with self.assertRaises(OSError): export_video(scene, output, ffmpeg='/definitely/missing/ffmpeg')
            if shutil.which('false'):
                with self.assertRaises((OSError, RuntimeError)): export_video(scene, output, ffmpeg=shutil.which('false'))


if __name__ == '__main__':
    unittest.main()
