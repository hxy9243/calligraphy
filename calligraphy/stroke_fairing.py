"""Experimental constrained contact fairing; a geometric prior, not brush physics.

Minimize squared displacement plus strength * squared second differences in
station index. Freeze two entry/exit stations and median-derived turns. Width
and angle mode decouples center motion, contact magnitude and orientation.
"""
from __future__ import annotations
import copy
import numpy as np
from .stroke_ir import validate_program, SCHEMA_VERSION


def fair_values(values, strength, fixed):
    """Solve a quadratic fairing objective with exact landmark constraints."""
    values = np.asarray(values, float)
    n = len(values)
    if not np.isfinite(strength) or strength < 0:
        raise ValueError('strength must be finite and nonnegative')
    if n < 3 or strength == 0:
        return values.copy()
    differences = np.diff(np.eye(n), n=2, axis=0)
    lhs = np.eye(n) + strength * differences.T @ differences
    fixed = sorted(set(fixed))
    free = [i for i in range(n) if i not in fixed]
    result = values.copy()
    if free:
        rhs = values[free] - lhs[np.ix_(free, fixed)] @ values[fixed]
        result[free] = np.linalg.solve(lhs[np.ix_(free, free)], rhs)
    return result


def turn_landmarks(stations, guide):
    """Map guide bends >=45 degrees onto observed contact centers."""
    centers = np.asarray(stations).mean(axis=1)
    guide = np.asarray(guide, float)
    fixed = {0, 1, len(centers)-2, len(centers)-1}
    for i in range(1, len(guide)-1):
        before, after = guide[i]-guide[i-1], guide[i+1]-guide[i]
        norm = np.linalg.norm(before)*np.linalg.norm(after)
        if norm <= 1e-12:
            continue
        angle = np.arccos(np.clip(before @ after / norm, -1, 1))
        if angle >= np.pi/4:
            station = int(np.argmin(np.linalg.norm(centers-guide[i], axis=1)))
            fixed.update(range(max(0,station-1), min(len(centers),station+2)))
    return sorted(fixed)


def fair_program(program, guides, *, mode='rails', strength=1.0):
    """Return an independently replayable IR copy with fixed geometric settings.

    No outline mask is used. Strength measures regularity relative to station
    displacement. Station spacing is inherited from the frozen baseline; this
    is intentionally not an arc-length-invariant physical model.
    """
    validate_program(program)
    if program['schemaVersion'] != SCHEMA_VERSION:
        raise ValueError('fairing requires paired-contact IR 0.2')
    if mode not in ('rails', 'motion'):
        raise ValueError('mode must be rails or motion')
    if not np.isfinite(strength) or strength < 0:
        raise ValueError('strength must be finite and nonnegative')
    if len(guides) != len(program['strokes']):
        raise ValueError('one ordered guide is required per stroke')
    result = copy.deepcopy(program)
    for original, output, guide in zip(program['strokes'], result['strokes'], guides):
        geometry = original['geometry']
        points = np.asarray(geometry['stations'], float)
        guide = np.asarray(guide, float)
        if guide.ndim != 2 or guide.shape[1] != 2 or not np.isfinite(guide).all() or len(guide)<2:
            raise ValueError('guide must contain finite ordered [x,y] points')
        fixed = sorted(set(turn_landmarks(points, guide)) | set(geometry['corners']))
        if mode == 'rails':
            fitted = fair_values(points.reshape(len(points),4), strength, fixed).reshape(points.shape)
        else:
            centers = points.mean(axis=1)
            vector = points[:,1]-points[:,0]
            widths = np.linalg.norm(vector,axis=1)
            valid = np.flatnonzero(widths > 1e-10)
            if not len(valid):
                raise ValueError('contact width must be nonzero somewhere')
            angles = np.unwrap(np.arctan2(vector[valid,1],vector[valid,0]))
            angles = np.interp(np.arange(len(points)),valid,angles)
            centers = fair_values(centers, strength, fixed)
            widths = np.maximum(fair_values(widths, strength, fixed),0)
            angles = fair_values(angles, strength, fixed)
            vector = np.column_stack([np.cos(angles),np.sin(angles)])*widths[:,None]
            fitted = np.stack([centers-vector/2,centers+vector/2],axis=1)
            fitted[fixed] = points[fixed]
        output['geometry']['stations'] = np.clip(fitted,0,1).tolist()
        # Preserve turn landmarks as interpolation corners as well as fixed points.
        output['geometry']['corners'] = sorted(set(geometry['corners']) | {
            i for i in fixed if 1 < i < len(points)-2 and i-1 in fixed and i+1 in fixed})
    result['provenance']['contactFairing'] = {'mode': mode, 'strength': float(strength),
        'landmarks': 'two endpoint stations; guide bends >=45 degrees and neighbors',
        'limitation': 'quadratic geometric prior in station index; no physical brush or pressure inference'}
    validate_program(result)
    return result


__all__ = ['fair_program', 'fair_values', 'turn_landmarks']
