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
# Spawn/import overhead outweighs fitting gains for short or mostly cached text.
PARALLEL_MIN_STROKES = 64


def _cache_key(character, glyph, metadata, outline_expansion):
    guide_hash = sha256(json.dumps(glyph, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    key = f"kai:{outline_expansion}:{character}:{guide_hash}:{metadata['engine_version']}:{metadata['engine_source_sha256']}"
    return key, guide_hash


def _prepare_one(task):
    character, glyph, cache_path, metadata, outline_expansion = task
    cache = ArtifactCache(cache_path)
    key, guide_hash = _cache_key(character, glyph, metadata, outline_expansion)
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
    return program


def _initialize_glyph_worker():
    # Each process owns its fit arrays; do not nest OpenCV's own worker pool.
    cv2.setNumThreads(1)


def prepare_kai(glyphs, cache_path=None, *, outline_expansion=0, workers=1):
    """Prepare unique glyphs, dispatching only cache misses to bounded processes.

    The default is the original serial path. Spawn avoids inheriting renderer,
    native-library or SQLite state from a threaded server. Existing per-key file
    locks make simultaneous requests share one fit; SQLite writes remain atomic.
    """
    from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
    import multiprocessing

    metadata = engine_metadata('kai-fitted')
    cache_path = cache_path or os.environ.get('CALLIGRAPHY_KAI_CACHE',
        str(Path.home() / '.local/share/calligraphy/kai-geometry.db'))
    cache = ArtifactCache(cache_path)
    workers = max(1, min(2, int(workers)))
    programs, missing = {}, {}
    for character, glyph in glyphs.items():
        key, guide_hash = _cache_key(character, glyph, metadata, outline_expansion)
        try:
            program = cache.get(key)
        except KeyError:
            missing[character] = (character, glyph, str(cache_path), metadata, outline_expansion)
        else:
            validate_program(program)
            if program['character'] != character or program['provenance'].get('template_sha256') != guide_hash:
                raise ValueError(f'Kai cache identity mismatch for {character}')
            programs[character] = program
    if workers > 1 and len(missing) > 1 and sum(len(task[1]['strokes']) for task in missing.values()) >= PARALLEL_MIN_STROKES:
        # At most two tasks in flight, not a future for every input character.
        executor = ProcessPoolExecutor(max_workers=min(workers, len(missing)),
            mp_context=multiprocessing.get_context('spawn'), initializer=_initialize_glyph_worker)
        pending = {}
        tasks = iter(missing.items())
        try:
            for _ in range(min(workers, len(missing))):
                character, task = next(tasks)
                pending[executor.submit(_prepare_one, task)] = character
            while pending:
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                # Check every completed result before submitting more work.
                for future in completed:
                    character = pending.pop(future)
                    programs[character] = future.result()
                for _ in completed:
                    item = next(tasks, None)
                    if item is not None:
                        character, task = item
                        pending[executor.submit(_prepare_one, task)] = character
        finally:
            for future in pending:
                future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)

    else:
        for character, task in missing.items():
            programs[character] = _prepare_one(task)
    return {character: programs[character] for character in glyphs}


class KaiScene(StyledContactScene):
    """Compile fitted IR and replay through the shared contact scene."""
    engine_type = 'kai-fitted'

    def __init__(self, plan, programs, appearance=None, transforms=None):
        self.programs = programs
        glyphs = {char: compile_program(program) for char, program in programs.items()}
        super().__init__(plan, glyphs, appearance, transforms)
