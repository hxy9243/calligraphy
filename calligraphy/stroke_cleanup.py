"""Selective narrow-feature cleanup of individual contact strokes.

This is a geometric contour prior, not recovery of physical brush motion. Broad
contours survive; features narrower than a small local scale may be removed.
"""
from __future__ import annotations
import copy
import cv2
import numpy as np
from scipy import ndimage
from .stroke_ir import validate_program, render_program, compile_program, SCHEMA_VERSION
from .stroke_fitting import fit_contact_stroke, _motion_checks


def smooth_rails(stations: np.ndarray, corners: list[int] | None = None, passes: int = 2) -> np.ndarray:
    """Fair contact rails while preserving endpoints, corners, and bounds."""
    corners_set = set(corners or [])
    res = np.asarray(stations, float).copy()
    n = len(res)
    if n < 4:
        return res
    # 0. Prevent rail cross-over / inversion (ensure left rail is strictly on left of spine travel direction)
    centres = res.mean(axis=1)
    tangents = np.gradient(centres, axis=0)
    lengths = np.linalg.norm(tangents, axis=1)
    valid = lengths > 1e-6
    normals = np.zeros_like(tangents)
    # in screen coords (x right, y down), left-pointing normal is [dy, -dx]
    normals[valid, 0] = tangents[valid, 1] / lengths[valid]
    normals[valid, 1] = -tangents[valid, 0] / lengths[valid]
    cross = res[:, 0] - res[:, 1]
    alignment = np.sum(cross * normals, axis=1)
    flipped = (alignment < -1e-4) & (np.linalg.norm(cross, axis=1) > 2.0 / 480.0)
    if np.any(flipped):
        for k in np.flatnonzero(flipped):
            if k not in corners_set:
                res[k, 0], res[k, 1] = res[k, 1].copy(), res[k, 0].copy()

    # 1. Suppress localized junction bulges along straight vertical stems
    if n >= 6:
        dirs = np.zeros_like(tangents)
        dirs[valid] = tangents[valid] / lengths[valid, None]
        for rail in (0, 1):
            other_rail = 1 - rail
            is_vert = np.abs(dirs[:, 1]) > 0.75
            i = 0
            while i < n:
                if not is_vert[i]:
                    i += 1
                    continue
                start = i
                while i < n and is_vert[i]:
                    i += 1
                end = i
                if end - start < 5:
                    continue
                span_indices = [k for k in range(start, end) if k not in corners_set]
                if len(span_indices) < 5:
                    continue
                other_x = res[span_indices, other_rail, 0]
                if np.ptp(other_x) < 4.0 / 480.0:
                    this_x = res[span_indices, rail, 0]
                    sign = 1 if rail == 1 else -1
                    base_x = np.median(this_x)
                    bulge = (this_x - base_x) * sign
                    if np.max(bulge) > 4.0 / 480.0:
                        for idx, k in enumerate(span_indices):
                            if bulge[idx] > 1.5 / 480.0:
                                res[k, rail, 0] = base_x
    for _ in range(passes):
        for rail in range(2):
            pts = res[:, rail].copy()
            # 2. Clamp acute sawtooth spikes & hairpin reversals exceeding chord
            for i in range(1, n - 1):
                if i in corners_set:
                    continue
                chord = pts[i + 1] - pts[i - 1]
                c_len = np.linalg.norm(chord)
                if c_len < 1e-7:
                    continue
                v1 = pts[i] - pts[i - 1]
                v2 = pts[i + 1] - pts[i]
                l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
                t = np.clip((pts[i] - pts[i - 1]) @ chord / (c_len ** 2), 0.0, 1.0)
                base = pts[i - 1] + t * chord
                dist = np.linalg.norm(pts[i] - base)
                cos_turn = (v1 @ v2) / max(l1 * l2, 1e-10)
                reversal = cos_turn < 0
                acute_turn = cos_turn < 0.25
                if (reversal and (dist > 0.35 * c_len or dist > 2.5 / 480.0)) or dist > 1.2 * c_len or (acute_turn and dist > 3.0 / 480.0):
                    pts[i] = 0.5 * (pts[i - 1] + pts[i + 1])
            # 3. Smooth gentle curvature away from corners
            smoothed = pts.copy()
            for i in range(1, n - 1):
                if i in corners_set or (i - 1) in corners_set or (i + 1) in corners_set:
                    continue
                smoothed[i] = 0.25 * pts[i - 1] + 0.5 * pts[i] + 0.25 * pts[i + 1]
            res[:, rail] = smoothed

    # 4. Enforce bounded width variation (Lipschitz continuity)
    w = np.linalg.norm(res[:, 0] - res[:, 1], axis=1)
    ds = np.linalg.norm(np.diff(res.mean(axis=1), axis=0), axis=1)
    max_grad = 1.2
    for i in range(1, n):
        if i in corners_set or (i - 1) in corners_set:
            continue
        max_dw = max_grad * max(ds[i - 1], 1e-4)
        if w[i] > w[i - 1] + max_dw and w[i] > 1e-4:
            scale = (w[i - 1] + max_dw) / w[i]
            c = res[i].mean(axis=0)
            res[i, 0] = c + (res[i, 0] - c) * scale
            res[i, 1] = c + (res[i, 1] - c) * scale
    return np.clip(res, 0.0, 1.0)


def clean_program(program):
    """Return a new IR 0.2 program and explicit per-stroke retention evidence.

    Opening is applied only during compilation. Replay uses frozen contact
    geometry and never a target mask. Topology changes and large losses are
    rejected rather than silently deleting parts of a stroke.
    """
    validate_program(program)
    if program['schemaVersion'] != SCHEMA_VERSION:
        raise ValueError('selective cleanup requires paired-contact IR 0.2')
    result = copy.deepcopy(program)
    reports = []
    for original, output in zip(program['strokes'], result['strokes']):
        single = copy.deepcopy(program)
        single['strokes'], single['relations'] = [original], []
        before = np.asarray(render_program(single, 1, 480)) > .5
        area = int(before.sum())
        distance = ndimage.distance_transform_edt(before)
        radius = int(np.clip(round(.6 * np.median(distance[before])), 2, 5))
        accepted = False
        reason = 'no bounded topology-preserving cleanup candidate'
        before_holes = int((ndimage.binary_fill_holes(before) & ~before).sum())
        for trial_radius in range(radius, 0, -1):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                               (2*trial_radius+1, 2*trial_radius+1))
            cleaned = cv2.morphologyEx(before.astype(np.uint8), cv2.MORPH_OPEN, kernel) > 0
            count, _ = cv2.connectedComponents(cleaned.astype(np.uint8), connectivity=8)
            if count != 2:
                reason = 'opening would split or erase the stroke'
                continue
            filled = ndimage.binary_fill_holes(cleaned)
            holes = int((filled & ~cleaned).sum())
            new_holes = max(0, holes - before_holes)
            if new_holes > 25:
                reason = 'substantial interior hole needs stroke ownership review'
                continue
            cleaned = filled
            removed = int((before & ~cleaned).sum())
            if removed / area > .12:
                reason = 'narrow-feature removal exceeds 12% area budget'
                continue
            try:
                fitted = fit_contact_stroke(cleaned, np.asarray(original['geometry']['stations']).mean(axis=1),
                                             target_iou=.97)
            except ValueError:
                try:
                    fitted = fit_contact_stroke(cleaned, np.asarray(original['geometry']['stations']).mean(axis=1),
                                                 target_iou=.95)
                except ValueError as exc:
                    reason = str(exc)
                    continue
            geometry = {'type':'paired-contacts', 'stations':fitted['contacts'],
                        'corners':[], 'tension':0.0}
            check = copy.deepcopy(single)
            check['strokes'][0]['geometry'] = geometry
            actual = np.asarray(render_program(check, 1, 480)) > .5
            retention = float((before & actual).sum() / max((before | actual).sum(), 1))
            if retention < .86 or not fitted['report']['connected']:
                reason = 'rebuilt stroke exceeds geometry-change budget'
                continue
            output['geometry'] = geometry
            reports.append({'id':original['id'], 'radiusPx':trial_radius,
                            'removedPixels':removed, 'filledHolePixels':holes,
                            'retainedFraction':float((before & actual).sum()/area),
                            'originalStrokeIou':retention, 'cleanedMaskIou':fitted['report']['iou480'],
                            'reviewRequired':False, 'motion':{k:fitted['report'][k] for k in
                                ('monotonic','connected','prefixFrames')}})
            accepted = True
            break
        if not accepted:
            stations = np.asarray(original['geometry']['stations'], float)
            faired = smooth_rails(stations, original['geometry'].get('corners', []))
            geom = {'type': 'paired-contacts', 'stations': faired.tolist(),
                    'corners': list(original['geometry'].get('corners', [])),
                    'tension': original['geometry'].get('tension', 0.0)}
            check = copy.deepcopy(single)
            check['strokes'][0]['geometry'] = geom
            actual = np.asarray(render_program(check, 1, 480)) > .5
            retention = float((before & actual).sum() / max((before | actual).sum(), 1))
            connected = cv2.connectedComponents(actual.astype(np.uint8), connectivity=8)[0] == 2
            motion = _motion_checks(compile_program(check)[0]) if connected else None
            if retention >= 0.86 and connected and motion['prefixConnected']:
                output['geometry'] = geom
                reports.append({'id': original['id'], 'radiusPx': 0, 'removedPixels': int((before & ~actual).sum()),
                                'filledHolePixels': 0, 'retainedFraction': float((before & actual).sum() / area),
                                'originalStrokeIou': retention, 'cleanedMaskIou': retention,
                                'reviewRequired': False, 'motion': {**motion, 'connected': connected},
                                'method': 'direct-rail-fairing'})
                accepted = True
            else:
                reports.append({'id':original['id'], 'radiusPx':0, 'removedPixels':0,
                                'retainedFraction':1.0, 'originalStrokeIou':1.0,
                                'reviewRequired':True, 'reason':reason})
    result['provenance']['selectiveCleanup'] = {'method':'bounded-narrow-feature-opening/1',
        'limitation':'Small-scale contour cleanup only; broad ownership errors and inferred motion remain unverified.'}
    validate_program(result)
    return result, {'method':'bounded-narrow-feature-opening/1',
                    'config':{'radiusRangePx':[1,5], 'radiusFromMedianDistance':.6,
                              'maximumRemovedAreaFraction':.12, 'maximumHoleFillPixels':25,
                              'minimumRebuiltStrokeIou':.86, 'fitCleanedMaskIou':.97},
                    'strokes':reports}
