"""Reviewed, font-specific ownership corrections; original ink is never refitted.

Rail intervals are editable review guides, not replacements for the source bank.
Sparse alpha clips and timed transfers are derived and stored only in the contact
cache. Each moved pixel keeps its original coverage and takes its reveal time
from the nearest painted pixel of the reviewed receiving stroke.
"""
from copy import deepcopy
from hashlib import sha256
import json

import numpy as np
from scipy.ndimage import distance_transform_edt

from .contact_stroke import ContactStroke, complete_stroke

FONT_SHA256 = 'e488981abc453c3136fe78dfb27203f5c380d62a5046620ff781e1e75bc5364d'
# Zero-based stroke, rail and station indices. Both source and smoothed geometry
# must match: a newly fitted bank needs another visual review, never stale cuts.
REVIEWS = {
    '明': {
        'source': 'b62362f38680108d2400ab9fa36bf3422f5118e0fbeb3484d2ccaaebee5c7d89',
        'prepared': '0e129e6c88c01e3f4e50534bb8f97973bd1938ffbc447c221c806cdd4fe50e1e',
        'donor': 4, 'owners': [5, 6, 7],
        'cuts': [(0, 18, 30), (0, 39, 47), (1, 29, 39), (1, 47, 55), (1, 55, 64)],
    },
    '月': {
        'source': '43291bf64ee72af035c004c39625a8320ce71408376ad2922933251a25fabd5f',
        'prepared': '0a1a3039a933520dd55a31a391bdfae58f2985080535a1af07a617fa7b4132c8',
        'donor': 0, 'owners': [1, 2, 3],
        'cuts': [(0, 14, 31), (0, 32, 41), (1, 17, 31), (1, 41, 57)],
    },
    '清': {
        'source': '2cc42175ad788f11298eff6f361021b105c01d0221d366a41ee58b8faeef7e84',
        'prepared': '28a003257f0ce2b183b1a78bcabe29c9bd0e2c45f0aba0a88b0932e62f867922',
        'donor': 6, 'owners': [4, 5],
        # Preserve the left entry nailhead and the right terminal.
        'cuts': [(1, 25, 36)],
    },
}


def geometry_digest(strokes):
    return sha256(json.dumps(strokes, sort_keys=True, ensure_ascii=False,
                             allow_nan=False).encode()).hexdigest()


def reviewed_envelope(stroke, cuts):
    result = deepcopy(stroke)
    segment = (max(result['segments'], key=lambda s: complete_stroke(s['stroke']).sum())['stroke']
               if 'segments' in result else result)
    rails = np.asarray(segment['contacts'], dtype=float)
    changed = set()
    for rail, start, end in cuts:
        rails[start:end+1, rail] = np.linspace(rails[start, rail], rails[end, rail], end-start+1)
        changed.update(range(start+1, end))
    segment['contacts'] = rails.tolist()
    segment['corners'] = [i for i in segment.get('corners', []) if i not in changed]
    segment['features'] = [f for f in segment.get('features', []) if f['station'] not in changed]
    return result


def transfer_ownership(strokes, donor, owners, envelope):
    """Move only clipped source pixels, retaining every final alpha exactly.

    The reviewed candidate owners constrain assignment; nearest distance alone
    is deliberately not allowed to choose arbitrary strokes in a glyph.
    """
    if (not owners or len(set(owners)) != len(owners) or donor in owners
            or any(i < 0 or i >= len(strokes) for i in [donor, *owners])):
        raise ValueError('Expected a donor and distinct receiving strokes')
    if any('ownership' in strokes[i] for i in [donor, *owners]):
        raise ValueError('Cannot overwrite existing contact ownership')
    masks = [complete_stroke(s) for s in strokes]
    original = masks[donor]
    limit = complete_stroke(envelope)
    moved = original > limit
    indices = np.flatnonzero(moved)
    result = deepcopy(strokes)
    result[donor]['ownership'] = {'clip': np.column_stack((indices, limit.ravel()[indices])).tolist()}
    distances, neighbors = [], []
    for owner in owners:
        distance, nearest = distance_transform_edt(masks[owner] < .5, return_indices=True)
        distances.append(distance)
        neighbors.append(nearest)
    assigned = np.argmin(distances, axis=0)
    transfers = []
    for position, owner in enumerate(owners):
        selected = np.flatnonzero(moved & (assigned == position))
        if not len(selected):
            continue
        # Sample the existing contact painter, including its segment timing.
        # Taking first coverage is monotone and never changes the outer schedule.
        arrival = np.ones((480, 480), np.float32)
        painter = ContactStroke(strokes[owner])
        for progress in np.linspace(1/64, 1, 64):
            # Match the solid-ink threshold used to select the nearest pixel.
            # An antialias fringe alone must not reveal a solid detached patch.
            painted = painter.advance(float(progress)) >= .5
            arrival[painted] = np.minimum(arrival[painted], progress)
        nearest = neighbors[position].reshape(2, -1)[:, selected]
        reveal = arrival[nearest[0], nearest[1]]
        result[owner]['ownership'] = {'patches': np.column_stack(
            (selected, original.ravel()[selected], reveal)).tolist()}
        transfers.append({'ownerStroke': owner+1, 'pixels': len(selected),
                          'firstProgress': float(reveal.min()), 'lastProgress': float(reveal.max())})
    before = np.maximum.reduce(masks)
    after = np.maximum.reduce([complete_stroke(s) for s in result])
    if not np.array_equal(before, after):
        raise ValueError('Reviewed ownership must preserve complete glyph alpha exactly')
    return result, {'donorStroke': donor+1, 'transfers': transfers,
                    'finalAlphaEqual': True, 'movedPixels': len(indices)}


def apply_reviewed_ownership(character, source_strokes, prepared, source):
    """Return unchanged geometry unless this exact font and both fits were reviewed."""
    review = REVIEWS.get(character)
    if review is None or source.get('font', {}).get('sha256') != FONT_SHA256:
        return prepared, None
    if (geometry_digest(source_strokes) != review['source']
            or geometry_digest(prepared) != review['prepared']):
        return prepared, {'status': 'skipped', 'reason': 'reviewed-geometry-mismatch'}
    envelope = reviewed_envelope(prepared[review['donor']], review['cuts'])
    corrected, report = transfer_ownership(prepared, review['donor'], review['owners'], envelope)
    report.update({'status': 'applied', 'review': 'shoujin-attached/1',
                   'sourceGeometrySha256': review['source'],
                   'preparedGeometrySha256': review['prepared']})
    return corrected, report
