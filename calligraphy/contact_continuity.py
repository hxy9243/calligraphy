"""Recover collapsed inferred traversals in old banks without changing final ink.

Only large interior schedule holes nominate a refit. The normal font fitter's
bounded registration retry must close those holes while retaining the rendered
shape. All work stays in the derived cache; source banks remain untouched.
"""
from copy import deepcopy
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt

from .contact_stroke import ContactStroke, complete_stroke
from .font_fitting import iou, registered_fields
from .font_pipeline import fit_glyph
from .stroke_crossings import smooth_kai_contacts


def interior_gaps(strokes):
    found = []
    for index, stroke in enumerate(strokes):
        pieces = sorted(stroke.get('segments', []), key=lambda item: item['start'])
        if len(pieces) < 2:
            continue
        end = pieces[0]['end']
        for piece in pieces[1:]:
            if piece['start'] - end >= .2 and end >= .1 and piece['start'] <= .9:
                found.append(index)
                break
            end = max(end, piece['end'])
    return found


def preserve_final_ink(strokes, target):
    """Project only raster edge differences onto the old complete glyph alpha.

    Contacts still determine traversal. Missing edge pixels inherit the nearest
    solid contact's first coverage; no whole glyph bitmap is revealed at the end.
    Existing ownership clips/patches are composed rather than overwritten.
    """
    target = np.asarray(target)
    if (target.shape != (480, 480) or not np.isfinite(target).all()
            or np.any(target < 0) or np.any(target > 1) or not strokes):
        raise ValueError('Expected strokes and finite 480x480 target alpha in [0,1]')
    masks = [complete_stroke(stroke) for stroke in strokes]
    if not any(np.any(mask >= .5) for mask in masks):
        raise ValueError('Expected at least one solid contact pixel')
    union = np.maximum.reduce(masks)
    missing = target > union
    selected = np.flatnonzero(missing)
    fields = [distance_transform_edt(mask < .5, return_indices=True) for mask in masks]
    for mask, (distance, _) in zip(masks, fields):
        if not np.any(mask >= .5):
            distance.fill(np.inf)
    distances, nearest = zip(*fields)
    assigned = np.argmin(np.stack(distances), axis=0)
    result = deepcopy(strokes)
    for index, (stroke, mask) in enumerate(zip(result, masks)):
        ownership = stroke.setdefault('ownership', {})
        clips = {int(row[0]): float(row[1]) for row in ownership.get('clip', [])}
        patches = {int(row[0]): [float(row[1]), float(row[2])]
                   for row in ownership.get('patches', [])}
        for pixel in np.flatnonzero(mask > target):
            cap = float(target.ravel()[pixel])
            clips[int(pixel)] = min(clips.get(int(pixel), 1.), cap)
        # Patches are deposited after clipping in ContactStroke.
        for pixel, value in patches.items():
            value[0] = min(value[0], float(target.ravel()[pixel]))
        pixels = selected[assigned.ravel()[selected] == index]
        if len(pixels):
            arrival = np.ones(target.shape, np.float32)
            painter = ContactStroke(strokes[index])
            for progress in np.linspace(1/64, 1, 64):
                painted = painter.advance(float(progress)) >= .5
                arrival[painted] = np.minimum(arrival[painted], progress)
            neighbors = nearest[index].reshape(2, -1)[:, pixels]
            times = arrival[neighbors[0], neighbors[1]]
            for pixel, time in zip(pixels, times):
                patches[int(pixel)] = [float(target.ravel()[pixel]),
                                       min(patches.get(int(pixel), [0., 1.])[1], float(time))]
        ownership['clip'] = [[pixel, value] for pixel, value in sorted(clips.items())]
        ownership['patches'] = [[pixel, *value] for pixel, value in sorted(patches.items())]
        if not clips and not patches:
            del stroke['ownership']
    if not np.array_equal(target, np.maximum.reduce([complete_stroke(s) for s in result])):
        raise ValueError('Continuity repair must preserve complete glyph alpha exactly')
    return result


def repair_contact_continuity(character, source_strokes, prepared, template):
    candidates = interior_gaps(source_strokes)
    if not candidates or template is None:
        return prepared, None
    report = {'status': 'skipped', 'candidateStrokes': [i + 1 for i in candidates]}
    if any(stroke.get('ownership') for stroke in prepared):
        return prepared, {**report, 'reason': 'existing-ownership-correction'}
    target = np.maximum.reduce([complete_stroke(s) for s in prepared])
    try:
        diagnostics = {}
        gray = np.uint8(np.clip(255 * (1 - cv2.resize(target, (160, 160))), 0, 255))
        registered_fields(gray, template, diagnostics=diagnostics)
        repaired_indices = {row[0] for row in diagnostics['collapsed_intervals']}
        if not any(i in repaired_indices for i in candidates):
            return prepared, {**report, 'reason': 'unrelated-registration-collapse'}
        strong = {}
        registered_fields(gray, template, tightness=2., diagnostics=strong)
        if strong['collapsed_intervals']:
            return prepared, {**report, 'reason': 'remaining-registration-collapse'}
        # An old rendered target already contains deformation artifacts, so its
        # registration IoU is not a reliable font-alignment score. Gate this
        # explicit retry on fitted geometry and exact-alpha retention instead.
        fitted, metrics = fit_glyph(character, target, template, tightness_candidates=(2.,))
        if metrics.get('guide_fallback_strokes') or metrics.get('review_required'):
            return prepared, {**report, 'reason': 'ambiguous-refit'}
        if len(fitted) != len(prepared) or any(i in interior_gaps(fitted) for i in candidates):
            return prepared, {**report, 'reason': 'unresolved-interior-gap'}
        repaired, _ = smooth_kai_contacts(fitted, inferred_corners=True)
        union = np.maximum.reduce([complete_stroke(s) for s in repaired])
        retention = iou(union, target)
        if retention < .95:
            return prepared, {**report, 'reason': 'shape-retention-guard', 'glyphRetentionIoU': retention}
        # Do not restore a missing branch by timed pixels. Only a narrow raster
        # collar around the newly fitted contacts can receive alpha corrections.
        distance = distance_transform_edt(union < .5)
        if np.any((target > .5) & (distance > 5)):
            return prepared, {**report, 'reason': 'missing-body-guard'}
        repaired = preserve_final_ink(repaired, target)
    except ValueError as error:
        return prepared, {**report, 'reason': 'refit-unavailable', 'detail': str(error)}
    return repaired, {**report, 'status': 'applied', 'glyphRetentionIoU': retention,
                      'finalAlphaEqual': True, 'method': 'registration-continuity/1'}
