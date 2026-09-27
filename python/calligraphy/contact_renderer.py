"""Replay promoted contact glyphs with a geometry-independent text plan.

Rendering only: preparation/fitting remains in calligraphy-lab. This module does
not depend on the lab checkout, its caches, reference images or notebooks.
"""
import argparse
import hashlib
from importlib.resources import files
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image

from .brush_grammar import ContactBrush, complete


PAPER = (249, 246, 238)
INK = (28, 27, 24)
SIZE = 480


def style_manifest():
    return json.loads(files('calligraphy').joinpath('assets/contact/manifest.json').read_text())


def load_style(style):
    manifest = style_manifest()
    if style not in manifest['styles']:
        raise ValueError(f'Unknown contact style {style!r}; choose {", ".join(manifest["styles"])}')
    entry = manifest['styles'][style]
    raw = files('calligraphy').joinpath('assets/contact', entry['file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError(f'Contact glyph checksum mismatch for {style}')
    return json.loads(raw)


def finite(value, name, minimum=0, maximum=math.inf):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be finite and between {minimum} and {maximum}')
    return value


def validate_plan(plan, glyphs):
    if not isinstance(plan, dict) or plan.get('schemaVersion') != 1:
        raise ValueError('Expected text plan schemaVersion 1')
    for key in ('width', 'height'):
        n = finite(plan.get(key), key, 64, 8192)
        if not isinstance(n, int):
            raise ValueError(f'{key} must be an integer')
    duration = finite(plan.get('duration'), 'duration', 0.000001)
    step = finite(plan.get('strokeSeconds'), 'strokeSeconds', 0.000001, 60)
    schedule = plan.get('schedule')
    if not isinstance(schedule, list) or not 1 <= len(schedule) <= 512 or not all(isinstance(e, dict) for e in schedule):
        raise ValueError('Expected 1–512 scheduled glyphs')
    missing = list(dict.fromkeys(e.get('character') for e in schedule if e.get('character') not in glyphs))
    if missing:
        raise ValueError('Missing prepared contact glyphs: ' + ' '.join(map(str, missing)))
    previous_end = 0
    for entry in schedule:
        character = entry['character']
        if entry.get('strokeCount') != len(glyphs[character]):
            raise ValueError(f'Stroke count mismatch for {character}')
        start = finite(entry.get('start'), 'start')
        end = finite(entry.get('end'), 'end')
        length = finite(entry.get('duration'), 'glyph duration', 0.000001)
        if start + 1e-8 < previous_end or end > duration + 1e-8 or not math.isclose(end - start, len(glyphs[character]) * step, abs_tol=1e-8) or not math.isclose(length, end - start, abs_tol=1e-8):
            raise ValueError('Inconsistent or overlapping glyph schedule')
        previous_end = end
        size = finite(entry.get('size'), 'size', 1)
        x, y = finite(entry.get('x'), 'x'), finite(entry.get('y'), 'y')
        if x + size > plan['width'] + 1e-6 or y + size > plan['height'] + 1e-6:
            raise ValueError('Glyph cell is outside the page')
    return plan


class ContactScene:
    """Same contact deposition as the lab; shared-plan placement and seeking."""

    def __init__(self, plan, glyphs):
        # Do not let caller mutations change a scene midway through a render.
        self.glyphs = json.loads(json.dumps(glyphs))
        self.plan = validate_plan(json.loads(json.dumps(plan)), self.glyphs)
        self._complete = {}
        self._patches = {}
        self._active = None
        self._last_time = -1

    def glyph_mask(self, character):
        if character not in self._complete:
            mask = np.zeros((SIZE, SIZE), np.float32)
            for stroke in self.glyphs[character]:
                mask = np.maximum(mask, complete(stroke))
            self._complete[character] = mask
        return self._complete[character].copy()

    def _partial(self, index, entry, time):
        if self._active is None or self._active['index'] != index:
            self._active = {'index': index, 'painters': [ContactBrush(s) for s in self.glyphs[entry['character']]],
                            'ink': np.zeros((SIZE, SIZE), np.float32), 'finished': set()}
        active = self._active
        elapsed = (time - entry['start']) / self.plan['strokeSeconds']
        for i, painter in enumerate(active['painters']):
            if i in active['finished'] or elapsed < i:
                continue
            progress = min(1, elapsed - i)
            active['ink'] = np.maximum(active['ink'], painter.advance(progress))
            if progress >= 1:
                active['finished'].add(i)
        return active['ink']

    @staticmethod
    def _patch(mask, size):
        # The lab renderer's coverage -> alpha -> paper compositing operation.
        alpha = Image.fromarray(np.uint8(np.clip(mask, 0, 1) * 255)).resize((size, size), Image.Resampling.LANCZOS)
        patch = Image.new('RGBA', (size, size), INK + (0,))
        patch.putalpha(alpha)
        return patch

    def frame(self, time):
        time = float(finite(time, 'time', -math.inf))
        time = min(self.plan['duration'], max(0, time))
        if time < self._last_time:
            self._active = None
        self._last_time = time
        page = Image.new('RGB', (self.plan['width'], self.plan['height']), PAPER)
        for index, entry in enumerate(self.plan['schedule']):
            if time <= entry['start']:
                break
            size = max(1, round(entry['size'] * .92))
            x, y = round(entry['x'] + entry['size'] * .04), round(entry['y'] + entry['size'] * .04)
            if time >= entry['end']:
                key = (entry['character'], size)
                if key not in self._patches:
                    self._patches[key] = self._patch(self.glyph_mask(entry['character']), size)
                patch = self._patches[key]
                if self._active and self._active['index'] == index:
                    # Complete via the same deposition before checking equivalence.
                    accumulated = self._partial(index, entry, entry['end'])
                    np.testing.assert_array_equal(accumulated, self.glyph_mask(entry['character']))
                    self._active = None
            else:
                patch = self._patch(self._partial(index, entry, time), size)
            page.paste(patch, (x, y), patch)
        return page


def export_png(scene, output, time=None):
    time = scene.plan['duration'] if time is None else finite(time, 'time', 0, scene.plan['duration'])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    scene.frame(time).save(output, format='PNG')


def export_video(scene, output, fps=24, speed=1, ffmpeg='ffmpeg'):
    finite(fps, 'fps', 1, 240)
    if not isinstance(fps, int):
        raise ValueError('fps must be an integer')
    finite(speed, 'speed', 0.000001, 10)
    width, height = scene.plan['width'], scene.plan['height']
    if width % 2 or height % 2:
        raise ValueError('Video width and height must be even')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([ffmpeg, '-y', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', f'{width}x{height}', '-framerate', str(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
        '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)], stdin=subprocess.PIPE)
    count = math.ceil(scene.plan['duration'] * fps / speed)
    try:
        for i in range(count):
            # Include exact completion in the last frame, even at low FPS.
            time = scene.plan['duration'] if i == count - 1 else i / fps * speed
            process.stdin.write(scene.frame(time).tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError('ffmpeg failed')
    except BaseException:
        try:
            process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.kill()
        process.wait()
        raise
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--style', required=True, choices=tuple(style_manifest()['styles']))
    parser.add_argument('--describe', action='store_true')
    args = parser.parse_args()
    glyphs = load_style(args.style)
    if args.describe:
        print(json.dumps({'style': args.style, 'strokeCounts': {c: len(s) for c, s in glyphs.items()},
                          'source': style_manifest()['styles'][args.style]}, ensure_ascii=False))
        return
    request = json.load(sys.stdin)
    scene = ContactScene(request['plan'], glyphs)
    output = request['output']
    suffix = Path(output).suffix.lower()
    if suffix == '.png':
        export_png(scene, output, request.get('time'))
    elif suffix == '.mp4':
        export_video(scene, output, request.get('fps', 24), request.get('speed', 1), request.get('ffmpeg', 'ffmpeg'))
    else:
        raise ValueError('Contact styles export PNG or MP4, not SVG')
    print(json.dumps({'output': output, 'style': args.style, 'characters': len(scene.plan['schedule'])}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        print(f'Contact render failed: {error}', file=sys.stderr)
        sys.exit(1)
