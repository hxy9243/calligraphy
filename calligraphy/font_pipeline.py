"""Prepare and register local font styles for the contact renderer.

Fonts supply silhouettes, Hanzi Writer records supply topology/order, and the
registration/contact fitter infers geometry. No network I/O occurs here.
"""
from contextlib import contextmanager
from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
import sys

import cv2
from fontTools.ttLib import TTFont
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .contact_stroke import complete_stroke
from .engine_metadata import engine_metadata
from .brush_grammar import validate
from .font_fitting import registered_fields, smooth_decomposition, ordered_guide, contacts_from_layer, iou

PIPELINE_VERSION = 'font-contact-v1'
RESERVED = {'kai', 'yan', 'lishu', 'liu', 'yan-contact'}
TIGHTNESS_CANDIDATES = (0.3, 0.5, 0.15, 0.08)


def style_path(style):
    if not isinstance(style, str) or not re.fullmatch(r'[a-z][a-z0-9 -]{0,79}', style):
        raise ValueError('Font style names must start with a lowercase letter and contain letters, digits, spaces or hyphens')
    slug = re.sub(r'[ -]+', '-', style.strip())
    if slug in RESERVED:
        raise ValueError(f'{style} is a reserved built-in style')
    root = Path(os.environ.get('CALLIGRAPHY_STYLE_DIR', Path.home() / '.local/share/calligraphy/styles'))
    return root / f'{slug}.json'


def registered_styles():
    root = style_path('registry-probe').parent
    styles = []
    for path in sorted(root.glob('*.json')):
        if path.name.startswith('.'):
            continue
        bank = load_bank(path.stem)
        styles.append({'style': bank['style'], 'prepared': len(bank['glyphs']), 'preparable': True})
    return styles


def load_bank(style):
    path = style_path(style)
    if not path.exists():
        raise ValueError(f'Unknown contact style: {style}. Register a font with npm run prepare:font first.')
    bank = json.loads(path.read_text())
    if bank.get('schemaVersion') != 1 or bank.get('pipeline') != PIPELINE_VERSION:
        raise ValueError('Unsupported font bank version; prepare it with a compatible engine')
    expected = sha256(json.dumps(bank['glyphs'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if expected != bank['geometry_sha256']:
        raise ValueError('Font bank geometry checksum mismatch')
    return bank


@contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def write_bank(path, bank):
    bank['geometry_sha256'] = sha256(json.dumps(bank['glyphs'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix='.font-bank-', suffix='.json')
    try:
        with os.fdopen(handle, 'w') as stream:
            json.dump(bank, stream, ensure_ascii=False, separators=(',', ':'))
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def target_masks(font_path, characters):
    with TTFont(font_path) as font:
        cmap = font.getBestCmap()
        missing = [c for c in characters if ord(c) not in cmap or cmap[ord(c)] == '.notdef']
        if missing:
            raise ValueError('Missing font glyphs: ' + ' '.join(missing))
    font = ImageFont.truetype(str(font_path), 420)
    for char in characters:
        box = font.getbbox(char)
        image = Image.new('L', (box[2] - box[0] + 8, box[3] - box[1] + 8), 0)
        ImageDraw.Draw(image).text((4 - box[0], 4 - box[1]), char, font=font, fill=255)
        bounds = image.getbbox()
        if bounds is None:
            raise ValueError(f'Empty font glyph: {char}')
        crop = image.crop(bounds)
        scale = 420 / max(crop.size)
        crop = crop.resize(tuple(max(1, round(s * scale)) for s in crop.size), Image.Resampling.LANCZOS)
        mask = Image.new('L', (480, 480), 0)
        mask.paste(crop, ((480 - crop.width) // 2, (480 - crop.height) // 2))
        yield char, np.asarray(mask, dtype=np.float32) / 255


def validate_template(glyph):
    if not isinstance(glyph, dict):
        raise ValueError('Expected a stroke template object')
    strokes, medians = glyph.get('strokes'), glyph.get('medians')
    if not isinstance(strokes, list) or not 1 <= len(strokes) <= 128 or not isinstance(medians, list) or len(strokes) != len(medians):
        raise ValueError('Expected 1–128 matching strokes and medians')
    for outline, median in zip(strokes, medians):
        if not isinstance(outline, str) or not re.fullmatch(r'[MmZzLlHhVvCcSsQqTtAa\d\s.,+\-eE]+', outline) or not outline.lstrip().startswith(('M', 'm')):
            raise ValueError('Expected SVG path data, not markup')
        points = np.asarray(median, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 2 or not np.isfinite(points).all() or np.linalg.norm(np.diff(points, axis=0), axis=1).sum() < 1:
            raise ValueError('Expected a nondegenerate finite median path')


def fit_layer(layer, progress, name):
    # The old lab fitter selected the largest contour. Keep disconnected ink
    # under the SAME scheduled stroke, with per-piece phase intervals.
    from scipy.ndimage import gaussian_filter
    mask = np.uint8(gaussian_filter(layer, .65) > .45)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    components = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 3]
    if not components:
        mask = np.uint8(gaussian_filter(layer, .65) > .20)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        components = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 2]
    if not components:
        raise ValueError(f'Empty inferred stroke: {name}')
    guide = ordered_guide(layer, progress)
    if len(components) == 1:
        return contacts_from_layer(layer, guide, name)
    segments = []
    support = layer > .25
    if not support.any():
        support = layer > .10
    lo, hi = np.quantile(progress[support], [.005, .995])
    for i in components:
        component = labels == i
        # A small collar retains antialiasing; connected components are disjoint.
        collar = cv2.dilate(component.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        piece = layer * collar
        points = np.column_stack(np.where(component))[:, ::-1]
        values = progress[component]
        a, b = np.quantile(values, [.005, .995])
        piece_guide = guide[(np.linspace(lo, hi, len(guide)) >= a) & (np.linspace(lo, hi, len(guide)) <= b)]
        if len(piece_guide) < 2:
            first, last = points[np.argmin(values)], points[np.argmax(values)]
            if np.linalg.norm(last - first) < 1:
                centered = points - points.mean(0)
                axis = np.linalg.svd(centered, full_matrices=False)[2][0]
                projection = centered @ axis
                first, last = points[np.argmin(projection)], points[np.argmax(projection)]
            piece_guide = np.array([first, last])
        fitted = contacts_from_layer(piece, piece_guide, name)
        validate(fitted)
        start = float(np.clip((a - lo) / max(hi - lo, 1e-6), 0, .99))
        end = float(np.clip((b - lo) / max(hi - lo, 1e-6), start + .01, 1))
        segments.append({'start': start, 'end': end, 'stroke': fitted})
    return {'name': name, 'segments': sorted(segments, key=lambda s: s['start'])}


def fit_glyph(character, target, glyph):
    validate_template(glyph)
    gray = np.uint8(np.clip(255 * (1 - cv2.resize(target, (160, 160))), 0, 255))
    tightness_candidates = TIGHTNESS_CANDIDATES
    for attempt, tightness in enumerate(tightness_candidates):
        try:
            warped, phase = registered_fields(gray, glyph, tightness=tightness)
        except TypeError:
            warped, phase = registered_fields(gray, glyph)
        layers, phases, _ = smooth_decomposition(warped, phase, target)
        strokes, scores, contributions = [], [], []
        ink = np.zeros_like(target)
        try:
            for index, (layer, progress) in enumerate(zip(layers, phases)):
                try:
                    stroke = fit_layer(layer, progress, f'{character} stroke {index + 1}')
                except ValueError as error:
                    if attempt == len(tightness_candidates) - 1 and 'Empty inferred stroke' in str(error):
                        try:
                            from .font_fitting import ribbon_envelope, ordered_guide
                            rmask, rphase = ribbon_envelope(warped[index], phase[index], target.shape)
                            guide = ordered_guide(rmask.astype(np.float32), rphase)
                            pairs = np.stack([guide, guide], axis=1)
                            stroke = {
                                'name': f'{character} stroke {index + 1}',
                                'contacts': pairs.tolist(),
                                'corners': [],
                                'tension': 0.5,
                                'features': [{'station': 1, 'kind': 'entry-press'}, {'station': len(pairs)-2, 'kind': 'lift'}]
                            }
                            validate(stroke)
                        except Exception:
                            raise ValueError(f'Cannot fit {character} stroke {index + 1}: {error}') from error
                    else:
                        raise ValueError(f'Cannot fit {character} stroke {index + 1}: {error}') from error
                mask = complete_stroke(stroke)
                after = np.maximum(ink, mask)
                contributions.append(float((after - ink).sum()))
                scores.append(iou(mask, layer))
                strokes.append(stroke)
                ink = after
            break
        except ValueError:
            if attempt == len(tightness_candidates) - 1:
                raise
    metrics = {'character': character, 'stroke_count': len(strokes), 'silhouette_iou': iou(ink, target),
               'min_inferred_stroke_iou': min(scores), 'no_new_ink_strokes': [i + 1 for i, c in enumerate(contributions) if c < .01],
               'template_sha256': sha256(json.dumps(glyph, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
    # This flags shape/ownership problems; it is not historical motion validation.
    metrics['review_required'] = metrics['silhouette_iou'] < .90 or min(scores) < .75 or bool(metrics['no_new_ink_strokes'])
    return strokes, metrics


def _fit_glyph_worker(args):
    char, target, glyph = args
    strokes, metrics = fit_glyph(char, target, glyph)
    return char, strokes, metrics, glyph


def prepare_style(style, glyphs, font_path=None, license_path=None, source=None, workers=8):
    if not isinstance(glyphs, dict) or not 1 <= len(glyphs) <= 512 or any(not isinstance(c, str) or len(c) != 1 for c in glyphs):
        raise ValueError('Supply a dictionary of 1–512 character templates')
    for glyph in glyphs.values():
        validate_template(glyph)
    workers = max(1, int(workers if workers is not None else 8))
    path = style_path(style)
    with locked(path):
        if path.exists():
            bank = load_bank(style)
            saved_font = Path(bank['font']['path'])
            if font_path and sha256(Path(font_path).read_bytes()).hexdigest() != bank['font']['sha256']:
                raise ValueError('Style already registered to another font; use a new style name')
            font_path = saved_font
        else:
            if not font_path or not license_path:
                raise ValueError('New font styles require --font and --license paths')
            font_path = Path(font_path).resolve()
            license_text = Path(license_path).read_text()
            if not license_text.strip():
                raise ValueError('Font license file is empty')
            original_path = font_path
            font_bytes = font_path.read_bytes()
            font_hash = sha256(font_bytes).hexdigest()
            cache = path.parent / 'fonts'
            cache.mkdir(exist_ok=True)
            font_path = cache.resolve() / f'{font_hash}{original_path.suffix.lower()}'
            handle, temporary = tempfile.mkstemp(dir=cache, prefix='.font-')
            try:
                with os.fdopen(handle, 'wb') as stream:
                    stream.write(font_bytes)
                os.replace(temporary, font_path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            bank = {'schemaVersion': 1, 'pipeline': PIPELINE_VERSION, 'style': style.strip(),
                    'font': {'path': str(font_path), 'sha256': sha256(font_path.read_bytes()).hexdigest(),
                             'source': source, 'original_path': str(original_path), 'license_text': license_text},
                    'glyphs': {}, 'metrics': {}, 'templates': {},
                    'template_provenance': {'format': 'Hanzi Writer strokes and medians', 'records': 'Caller supplied; per-character hashes and records retained'},
                    'interpretation': 'Automatically inferred stroke geometry; review flags are not a certification of motion or style.'}
        if sha256(Path(font_path).read_bytes()).hexdigest() != bank['font']['sha256']:
            raise ValueError('Registered font changed; use a new style name')
        missing = [c for c in glyphs if c not in bank['glyphs']]
        metadata = engine_metadata('font-contact') if missing else None
        bank.setdefault('glyph_metadata', {})
        tasks = [(char, target, glyphs[char]) for char, target in target_masks(font_path, missing)]
        if len(tasks) <= 1 or workers == 1:
            for char, target, glyph in tasks:
                strokes, metrics = fit_glyph(char, target, glyph)
                bank['glyphs'][char] = strokes
                bank['metrics'][char] = metrics
                bank['templates'][char] = glyph
                bank['glyph_metadata'][char] = dict(metadata)
                print(f'Prepared {char}: {len(strokes)} strokes, shape IoU {metrics["silhouette_iou"]:.3f}' + ('; review required' if metrics['review_required'] else ''), file=sys.stderr, flush=True)
        else:
            import concurrent.futures
            import multiprocessing as mp
            max_workers = min(workers, len(tasks))
            ctx = mp.get_context('spawn')
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx) as executor:
                for char, strokes, metrics, glyph in executor.map(_fit_glyph_worker, tasks):
                    bank['glyphs'][char] = strokes
                    bank['metrics'][char] = metrics
                    bank['templates'][char] = glyph
                    bank['glyph_metadata'][char] = dict(metadata)
                    print(f'Prepared {char}: {len(strokes)} strokes, shape IoU {metrics["silhouette_iou"]:.3f}' + ('; review required' if metrics['review_required'] else ''), file=sys.stderr, flush=True)
        write_bank(path, bank)
    return {'style': bank['style'], 'path': str(path), 'prepared': missing,
            'strokeCounts': {c: len(s) for c, s in bank['glyphs'].items()}, 'metrics': bank['metrics']}
