"""Conservative, font-independent repair of attached inferred-contact residue.

Only derived font contacts opt in. Candidates preserve source alpha and must
pass coupled partial-glyph checks before entering the preparation cache.
"""
from copy import deepcopy

import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt, grey_opening

from .contact_ownership import reviewed_envelope, transfer_ownership
from .contact_stroke import ContactStroke, complete_stroke

METHOD = 'automatic-contact-ownership/1'
MAX_CANDIDATES = 16
MIN_OWNER_MARGIN = 4.0
PROGRESS_SAMPLES = 65


def find_candidates(strokes):
    """Nominate supported interior rail peaks without glyph or font identities."""
    if len(strokes) < 2:
        return []
    masks = [complete_stroke(s) for s in strokes]
    distances = [distance_transform_edt(m < .5) for m in masks]
    found = {}
    for index, stroke in enumerate(strokes):
        if 'ownership' in stroke:
            continue
        part = (max(stroke['segments'], key=lambda p: complete_stroke(p['stroke']).sum())['stroke']
                if 'segments' in stroke else stroke)
        rails = np.asarray(part['contacts'], dtype=float)
        centers = rails.mean(1)
        chord = centers[-1] - centers[0]
        length = np.linalg.norm(chord)
        if length < 60 or np.linalg.norm(np.diff(centers, axis=0), axis=1).sum() > 1.25 * length:
            continue
        tangent = chord / length
        normal = np.array([-tangent[1], tangent[0]])
        width = np.median(np.abs((rails[:, 1] - rails[:, 0]) @ normal))
        for rail in (0, 1):
            points = rails[:, rail]
            along = (points - centers[0]) @ tangent
            outward = np.sign(np.median((points - rails[:, 1-rail]) @ normal))
            if outward == 0 or np.ptp(along) < 1:
                continue
            profile = ((points - centers[0]) @ normal) * outward
            axis = np.linspace(along.min(), along.max(), 480)
            order = np.argsort(along)
            sampled = np.interp(axis, along[order], profile[order])
            window = max(3, int(np.clip(width * 2, 18, 42) / np.ptp(axis) * 480))
            opened = grey_opening(sampled, size=window)
            delta = profile - np.interp(along, axis, opened)
            marked = ((delta > max(3., width * .3)) &
                      (along > .16 * length) & (along < .84 * length))
            groups = np.flatnonzero(np.diff(np.r_[False, marked, False])).reshape(-1, 2)
            for start, stop in groups:
                end = stop
                while start > 1 and delta[start-1] > 1:
                    start -= 1
                while end < len(rails)-2 and delta[end+1] > 1:
                    end += 1
                start, end = max(1, start-1), min(len(rails)-2, end+1)
                if (end-start < 2 or min(along[start], along[end]) < .12 * length
                        or max(along[start], along[end]) > .88 * length):
                    continue
                cut = (rail, int(start), int(end))
                envelope = reviewed_envelope(stroke, [cut])
                clean = complete_stroke(envelope)
                moved = (masks[index] > .5) & (clean < .5)
                area = int(moved.sum())
                if area < 25 or area > masks[index].sum() * .25:
                    continue
                if (cv2.connectedComponents(np.uint8(clean > .5))[0] !=
                        cv2.connectedComponents(np.uint8(masks[index] > .5))[0]):
                    continue
                # Include all neighbors in the confidence comparison. An already
                # corrected nearest owner must not make a farther one look valid.
                ranking = sorted((float(d[moved].mean()), j)
                                 for j, d in enumerate(distances) if j != index)
                distance, owner = ranking[0]
                margin = ranking[1][0] - distance if len(ranking) > 1 else None
                if ('ownership' in strokes[owner] or distance > max(12, width)
                        or (margin is not None and margin < MIN_OWNER_MARGIN)):
                    continue
                found[(index, cut)] = {
                    'donor': index, 'owner': owner, 'cut': list(cut), 'pixels': area,
                    'meanOwnerDistance': distance, 'ownerMargin': margin, 'envelope': envelope,
                }
    return sorted(found.values(), key=lambda p: (-p['pixels'], p['donor'], p['cut']))


def validate_ownership_motion(before, after, changed):
    """Check the coupled result, including intervening strokes and prior edits.

    Final alpha equality is exact. Connectivity is sampled at the transfer
    clock's 64 intervals and rejects new islands of four or more binary pixels.
    This guards animation mechanics; it does not certify historical pen motion.
    """
    old_masks = [complete_stroke(s) for s in before]
    new_masks = [complete_stroke(s) for s in after]
    if not np.array_equal(np.maximum.reduce(old_masks), np.maximum.reduce(new_masks)):
        return False, 'final-alpha-changed'
    if not changed:
        return True, None
    start, stop = min(changed), max(changed)
    old_prefix = np.maximum.reduce(old_masks[:start]) if start else np.zeros((480, 480), np.float32)
    new_prefix = np.maximum.reduce(new_masks[:start]) if start else np.zeros((480, 480), np.float32)
    for index in range(start, stop+1):
        painters = [ContactStroke(before[index]), ContactStroke(after[index])]
        last = np.zeros((480, 480), np.float32)
        for progress in np.linspace(0, 1, PROGRESS_SAMPLES):
            old, new = [painter.advance(float(progress)) for painter in painters]
            if not np.all(new >= last):
                return False, 'nonmonotonic-ink'
            last = new
            original = np.maximum(old_prefix, old) > .5
            proposed = np.maximum(new_prefix, new) > .5
            count, labels, stats, _ = cv2.connectedComponentsWithStats(np.uint8(proposed), 8)
            # Vectorized component support avoids scanning every component's
            # pixels repeatedly for complex glyphs.
            supported = np.bincount(labels[original], minlength=count) > 0
            if any(stats[k, cv2.CC_STAT_AREA] >= 4 and not supported[k] for k in range(1, count)):
                return False, 'new-detached-ink'
        if not np.array_equal(last, new_masks[index]):
            return False, 'completed-replay-mismatch'
        old_prefix = np.maximum(old_prefix, old_masks[index])
        new_prefix = np.maximum(new_prefix, new_masks[index])
    return True, None


def automatic_ownership(strokes):
    """Apply only noninteracting proposals that pass the combined motion guard."""
    result = deepcopy(strokes)
    proposals = find_candidates(strokes)
    reserved = {i for i, stroke in enumerate(strokes) if 'ownership' in stroke}
    changed, edits = set(), []
    for proposal in proposals[:MAX_CANDIDATES]:
        donor, owner = proposal['donor'], proposal['owner']
        entry = {key: value for key, value in proposal.items() if key != 'envelope'}
        entry.update(donorStroke=donor+1, ownerStroke=owner+1, accepted=False)
        if {donor, owner} & reserved:
            entry['reason'] = 'stroke-already-corrected'
        else:
            candidate, transfer = transfer_ownership(result, donor, [owner], proposal['envelope'])
            accepted, reason = validate_ownership_motion(strokes, candidate, changed | {donor, owner})
            entry.update(accepted=accepted, reason=reason, transfer=transfer)
            if accepted:
                result = candidate
                changed.update((donor, owner))
                reserved.update((donor, owner))
        edits.append(entry)
    return result, {'method': METHOD, 'candidateCount': len(proposals),
                    'candidateLimit': MAX_CANDIDATES,
                    'deferredCount': max(0, len(proposals)-MAX_CANDIDATES),
                    'acceptedCount': sum(e['accepted'] for e in edits),
                    'finalAlphaEqual': True, 'progressSamples': PROGRESS_SAMPLES,
                    'edits': edits}
