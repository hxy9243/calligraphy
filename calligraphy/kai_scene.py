"""Generic Han text prepared as fitted Kai IR, cached in SQLite and replayed."""
from hashlib import sha256
import json
import os
from pathlib import Path

import cv2

from .styled_contact_scene import StyledContactScene
from .artifact_cache import ArtifactCache
from .engine_metadata import engine_metadata
from .font_fitting import template
from .stroke_ir import compile_program, validate_program
from .stroke_fitting import fit_contact_stroke
from .stroke_crossings import smooth_kai_program

FIT_TARGET_IOU = .95
MINIMUM_FIT_IOU = .90


def prepare_kai(glyphs, cache_path=None, *, outline_expansion=0):
    metadata = engine_metadata('kai-fitted')
    cache_path = cache_path or os.environ.get('CALLIGRAPHY_KAI_CACHE',
        str(Path.home() / '.local/share/calligraphy/kai-geometry.db'))
    cache = ArtifactCache(cache_path)
    programs = {}
    for character, glyph in glyphs.items():
        guide_hash = sha256(json.dumps(glyph, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        key = f"kai:{outline_expansion}:{character}:{guide_hash}:{metadata['engine_version']}:{metadata['engine_source_sha256']}"
        with cache.lock(key):
            try:
                program = cache.get(key)
            except KeyError:
                layers, _, guides = template(glyph, return_guides=True, outline_expansion=outline_expansion)
                if len(layers) > 64:
                    raise ValueError(f'Kai IR supports at most 64 strokes: {character}')
                strokes, reports, targets = [], [], []
                for index, (layer, guide) in enumerate(zip(layers, guides)):
                    mask = cv2.resize(layer, (480, 480), interpolation=cv2.INTER_LINEAR) > .5
                    try:
                        fitted = fit_contact_stroke(mask, guide, target_iou=FIT_TARGET_IOU)
                    except ValueError as error:
                        raise ValueError(f'Cannot prepare Kai {character} stroke {index + 1}: {error}. '
                                         'Use --mode template for the legacy renderer.') from error
                    report = fitted['report']
                    # Keep optimizing for 95%, while permitting a usable fit at
                    # the separately configured 90% rejection boundary.
                    if not (report['iou480'] >= MINIMUM_FIT_IOU) or not report['prefixConnected'] or not report['monotonic']:
                        raise ValueError(f'Kai {character} stroke {index + 1} failed shape/motion validation; '
                                         'use --mode template to select the legacy renderer explicitly.')
                    strokes.append({'id': f's{index + 1}', 'kind': 'unclassified', 'duration': 1,
                                    'liftAfter': 0, 'geometry': {'type': 'paired-contacts',
                                    'stations': fitted['contacts'], 'corners': fitted['corners'],
                                    'tension': fitted['tension']}})
                    reports.append(report)
                    targets.append(mask)
                program = {'schemaVersion': 'kai-stroke-ir/0.2', 'character': character,
                           'script': 'kai', 'strokes': strokes, 'relations': [],
                           'provenance': {'source': 'Caller supplied Hanzi Writer outlines and medians',
                               'inferred': True, 'engine': metadata, 'outline_expansion': outline_expansion, 'template_sha256': guide_hash,
                               'fitTargetIoU': FIT_TARGET_IOU, 'minimumFitIoU': MINIMUM_FIT_IOU,
                               'strokeKinds': 'Unclassified; kind has no rendering semantics',
                               'fitReports': reports}}
                program, _ = smooth_kai_program(program, targets=targets, inferred_corners=True)
                validate_program(program)
                cache.put(key, program)
            validate_program(program)
            if program['character'] != character or program['provenance'].get('template_sha256') != guide_hash:
                raise ValueError(f'Kai cache identity mismatch for {character}')
        programs[character] = program
    return programs


class KaiScene(StyledContactScene):
    """Compile fitted IR and replay through the shared contact scene."""
    engine_type = 'kai-fitted'

    def __init__(self, plan, programs, appearance=None, transforms=None):
        self.programs = programs
        glyphs = {char: compile_program(program) for char, program in programs.items()}
        super().__init__(plan, glyphs, appearance, transforms)
