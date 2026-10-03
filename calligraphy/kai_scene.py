"""Generic Han text prepared as fitted Kai IR, cached in SQLite and replayed."""
import base64
from hashlib import sha256
import io
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .artifact_cache import ArtifactCache
from .contact_renderer import ContactScene
from .engine_metadata import engine_metadata
from .font_fitting import template
from .font_layers import FontLayerScene
from .spec import Appearance, Transforms
from .stroke_ir import compile_program, validate_program
from .stroke_fitting import fit_contact_stroke


def prepare_kai(glyphs, cache_path=None):
    metadata = engine_metadata('kai-fitted')
    cache_path = cache_path or os.environ.get('CALLIGRAPHY_KAI_CACHE',
        str(Path.home() / '.local/share/calligraphy/kai-geometry.db'))
    cache = ArtifactCache(cache_path)
    programs = {}
    for character, glyph in glyphs.items():
        guide_hash = sha256(json.dumps(glyph, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        key = f"kai:{character}:{guide_hash}:{metadata['engine_version']}:{metadata['engine_source_sha256']}"
        with cache.lock(key):
            try:
                program = cache.get(key)
            except KeyError:
                layers, _, guides = template(glyph, return_guides=True)
                if len(layers) > 64:
                    raise ValueError(f'Kai IR supports at most 64 strokes: {character}')
                strokes, reports = [], []
                for index, (layer, guide) in enumerate(zip(layers, guides)):
                    mask = cv2.resize(layer, (480, 480), interpolation=cv2.INTER_LINEAR) > .5
                    try:
                        fitted = fit_contact_stroke(mask, guide, target_iou=.95)
                    except ValueError as error:
                        raise ValueError(f'Cannot prepare Kai {character} stroke {index + 1}: {error}. '
                                         'Use --mode template for the legacy renderer.') from error
                    report = fitted['report']
                    if not report['targetReached'] or not report['prefixConnected'] or not report['monotonic']:
                        raise ValueError(f'Kai {character} stroke {index + 1} failed shape/motion validation; '
                                         'use --mode template to select the legacy renderer explicitly.')
                    strokes.append({'id': f's{index + 1}', 'kind': 'unclassified', 'duration': 1,
                                    'liftAfter': 0, 'geometry': {'type': 'paired-contacts',
                                    'stations': fitted['contacts'], 'corners': fitted['corners'],
                                    'tension': fitted['tension']}})
                    reports.append(report)
                program = {'schemaVersion': 'kai-stroke-ir/0.2', 'character': character,
                           'script': 'kai', 'strokes': strokes, 'relations': [],
                           'provenance': {'source': 'Caller supplied Hanzi Writer outlines and medians',
                               'inferred': True, 'engine': metadata, 'template_sha256': guide_hash,
                               'strokeKinds': 'Unclassified; kind has no rendering semantics',
                               'fitReports': reports}}
                validate_program(program)
                cache.put(key, program)
            validate_program(program)
            if program['character'] != character or program['provenance'].get('template_sha256') != guide_hash:
                raise ValueError(f'Kai cache identity mismatch for {character}')
        programs[character] = program
    return programs


class KaiScene(ContactScene):
    """Compile once and reuse contact painters; backwards seeks reset active ink."""
    parallel_frames = False
    engine_type = 'kai-fitted'

    def __init__(self, plan, programs, appearance=None, transforms=None):
        self.programs = programs
        glyphs = {char: compile_program(program) for char, program in programs.items()}
        super().__init__(plan, glyphs)
        self.appearance = appearance or Appearance()
        self.transforms = transforms or Transforms()
        self.width, self.height = plan['width'], plan['height']
        self.duration = plan['duration']

    _create_patch = FontLayerScene._create_patch

    def frame(self, time):
        time = float(time)
        if not np.isfinite(time):
            raise ValueError('time must be finite')
        time = min(self.duration, max(0, time))
        if time < self._last_time:
            self._active = None
        self._last_time = time
        page = Image.new('RGB', (self.width, self.height), self.appearance.paper_color)
        for index, entry in enumerate(self.plan['schedule']):
            if time <= entry['start']:
                break
            if time >= entry['end']:
                key = (entry['character'], entry['size'])
                if key not in self._patches:
                    self._patches[key] = self._create_patch(self.glyph_mask(entry['character']), entry['size'])
                patch = self._patches[key]
                if self._active and self._active['index'] == index:
                    self._active = None
            else:
                patch = self._create_patch(self._partial(index, entry, time), entry['size'])
            x = round(entry['x'] + entry['size'] / 2 - patch.width / 2)
            y = round(entry['y'] + entry['size'] / 2 - patch.height / 2)
            page.paste(patch, (x, y), patch)
        return page

    def frame_svg(self, time):
        # Same deposited pixels as PNG/video; SVG is a raster container here.
        stream = io.BytesIO()
        self.frame(time).save(stream, format='PNG')
        payload = base64.b64encode(stream.getvalue()).decode()
        characters = ''.join(f'<g data-character="{item["character"]}"/>' for item in self.plan['schedule'])
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
                f'viewBox="0 0 {self.width} {self.height}" data-engine="kai-fitted">'
                f'<image width="{self.width}" height="{self.height}" href="data:image/png;base64,{payload}"/>'
                f'{characters}</svg>')
