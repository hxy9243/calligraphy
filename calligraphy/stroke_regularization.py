"""Experimental geometric regularization for paired-contact stroke programs.

This module constrains an observed contact ribbon to a piecewise cubic centre
curve and piecewise cubic width/asymmetry curves.  It is a geometric prior for
experiments, not a physical brush, pressure, or bristle simulation.
"""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
from scipy.interpolate import PchipInterpolator

from .stroke_ir import SCHEMA_VERSION, validate_program

METHOD = "piecewise-cubic-ribbon/1"
GUIDE_WEIGHT = 0.55
RIDGE = 0.002
SPIKE_RATIO = 1.65
BOUND_EPSILON = 1e-06
MAX_CUBIC_SPANS = 3
MIN_TURN_SEPARATION = 0.15
TURN_THRESHOLD_RADIANS = float(np.deg2rad(24.0))


def _basis(t: np.ndarray) -> np.ndarray:
    u = 1.0 - t
    return np.column_stack([
        u**3,
        3 * u**2 * t,
        3 * u * t**2,
        t**3,
    ])


def _progress(values: np.ndarray) -> np.ndarray:
    distance = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(values, axis=0), axis=1))]
    if distance[-1] > 1e-12:
        return distance / distance[-1]
    return np.linspace(0.0, 1.0, len(values))


def _cubic_fit(values: np.ndarray, progress: np.ndarray | None) -> np.ndarray:
    """Fit one cubic Bezier while retaining its observed endpoints exactly."""
    n = len(values)
    if n <= 2:
        return values.copy()
    if progress is None:
        t = np.linspace(0.0, 1.0, n)
    else:
        t = (progress - progress[0]) / max(progress[-1] - progress[0], 1e-12)
    b = _basis(t)
    endpoints = b[:, :1] * values[:1] + b[:, 3:] * values[-1:]
    design = b[:, 1:3]
    lhs = design.T @ design + RIDGE * np.eye(2)
    rhs = design.T @ (values - endpoints)
    controls = np.linalg.solve(lhs, rhs)
    return endpoints + design @ controls


def _piecewise_fit(values: np.ndarray, breaks: list[int], progress: np.ndarray | None) -> np.ndarray:
    out = values.copy()
    for lo, hi in zip(breaks, breaks[1:]):
        out[lo:hi + 1] = _cubic_fit(
            values[lo:hi + 1],
            None if progress is None else progress[lo:hi + 1],
        )
    return out


def _infer_turns(centres: np.ndarray, progress: np.ndarray) -> list[int]:
    if len(centres) < 7:
        return []
    radius = max(2, len(centres) // 12)
    candidates = []
    for i in range(radius, len(centres) - radius):
        before = centres[i] - centres[i - radius]
        after = centres[i + radius] - centres[i]
        if min(np.linalg.norm(before), np.linalg.norm(after)) <= 1e-10:
            continue
        local_delta = np.diff(centres[i - radius:i + radius + 1], axis=0)
        cross = local_delta[:-1, 0] * local_delta[1:, 1] - local_delta[:-1, 1] * local_delta[1:, 0]
        signed = np.sign(cross[np.abs(cross) > 1e-8])
        if len(signed) and max(np.count_nonzero(signed > 0), np.count_nonzero(signed < 0)) / len(signed) < 0.75:
            continue
        angle = float(np.arccos(np.clip(before @ after / (np.linalg.norm(before) * np.linalg.norm(after)), -1.0, 1.0)))
        if angle >= TURN_THRESHOLD_RADIANS:
            candidates.append((angle, i))
    chosen: list[int] = []
    for _, index in sorted(candidates, reverse=True):
        if MIN_TURN_SEPARATION <= progress[index] <= 1.0 - MIN_TURN_SEPARATION:
            if all(abs(progress[index] - progress[j]) >= MIN_TURN_SEPARATION for j in chosen):
                chosen.append(index)
                if len(chosen) == MAX_CUBIC_SPANS - 1:
                    break
    return sorted(chosen)


def _keep_centres_bounded(fitted: np.ndarray, original: np.ndarray) -> np.ndarray:
    if np.all((fitted >= BOUND_EPSILON) & (fitted <= 1.0 - BOUND_EPSILON)):
        return fitted
    lo, hi = 0.0, 1.0
    for _ in range(40):
        alpha = (lo + hi) / 2.0
        trial = original + alpha * (fitted - original)
        if np.all((trial >= BOUND_EPSILON) & (trial <= 1.0 - BOUND_EPSILON)):
            lo = alpha
        else:
            hi = alpha
    return original + lo * (fitted - original)


def _limit_center_prickles(centres: np.ndarray, breaks: list[int]) -> np.ndarray:
    result = centres.copy()
    for i in range(1, len(centres) - 1):
        if i in breaks:
            continue
        chord = centres[i + 1] - centres[i - 1]
        chord2 = float(chord @ chord)
        if chord2 <= 1e-12:
            continue
        phase = np.clip((centres[i] - centres[i - 1]) @ chord / chord2, 0.0, 1.0)
        base = centres[i - 1] + phase * chord
        offset = centres[i] - base
        limit = 0.35 * np.sqrt(chord2)
        if np.linalg.norm(offset) > limit:
            result[i] = base + offset * (limit / np.linalg.norm(offset))
    return result


def _resample(values: np.ndarray, count: int) -> np.ndarray:
    old = _progress(values)
    new = np.linspace(0.0, 1.0, count)
    return np.column_stack([
        np.interp(new, old, values[:, axis])
        for axis in range(values.shape[1])
    ])


def _tangents(centres: np.ndarray, breaks: list[int]) -> np.ndarray:
    tangent = np.empty_like(centres)
    for lo, hi in zip(breaks, breaks[1:]):
        span = centres[lo:hi + 1]
        if len(span) > 2:
            local = np.gradient(span, axis=0)
        else:
            local = np.repeat((span[-1] - span[0])[None], len(span), axis=0)
        tangent[lo:hi + 1] = local
    for corner in breaks[1:-1]:
        before = centres[corner] - centres[max(0, corner - 1)]
        after = centres[min(len(centres) - 1, corner + 1)] - centres[corner]
        before /= max(np.linalg.norm(before), 1e-12)
        after /= max(np.linalg.norm(after), 1e-12)
        tangent[corner] = before + after
    lengths = np.linalg.norm(tangent, axis=1)
    valid = np.flatnonzero(lengths > 1e-10)
    if not len(valid):
        raise ValueError("regularized centreline has undefined direction")
    for index in np.flatnonzero(lengths <= 1e-10):
        nearest = valid[np.argmin(np.abs(valid - index))]
        tangent[index] = tangent[nearest]
    lengths = np.linalg.norm(tangent, axis=1)
    return tangent / lengths[:, None]


def _ray_limit(centres: np.ndarray, directions: np.ndarray) -> np.ndarray:
    limits = np.full(len(centres), np.inf)
    for axis in range(2):
        positive = directions[:, axis] > 1e-12
        negative = directions[:, axis] < -1e-12
        limits[positive] = np.minimum(
            limits[positive],
            (1.0 - centres[positive, axis]) / directions[positive, axis],
        )
        limits[negative] = np.minimum(
            limits[negative],
            -centres[negative, axis] / directions[negative, axis],
        )
    return np.maximum(limits - BOUND_EPSILON, 0.0)


def _curvature(centres: np.ndarray) -> float:
    delta = np.diff(centres, axis=0)
    length = np.linalg.norm(delta, axis=1)
    keep = length > 1e-10
    if keep.sum() < 2:
        return 0.0
    angles = np.unwrap(np.arctan2(delta[keep, 1], delta[keep, 0]))
    return float(np.sum(np.abs(np.diff(angles))))


def _roughness(width: np.ndarray) -> float:
    scale = max(float(np.mean(width)), 1e-12)
    if len(width) > 2:
        return float(np.sum(np.abs(np.diff(width, n=2)))) / scale
    return 0.0


def _width_fit(width: np.ndarray, progress: np.ndarray, breaks: list[int]) -> np.ndarray:
    knots = np.unique(np.r_[[0, 0.08, 0.25, 0.5, 0.75, 0.92, 1], progress[breaks]])
    values = np.interp(knots, progress, width)
    for i in range(1, len(values) - 1):
        neighbour = max(values[i - 1], values[i + 1], 1e-10)
        if values[i] > SPIKE_RATIO * neighbour:
            values[i] = SPIKE_RATIO * neighbour
    return np.maximum(PchipInterpolator(knots, values)(progress), 0.0)


def _join_inferred_turns(centres: np.ndarray, turns: list[int]) -> np.ndarray:
    result = centres.copy()
    for i in turns:
        if i < 2 or i + 2 >= len(result):
            continue
        direction = result[i + 2] - result[i - 2]
        length = np.linalg.norm(direction)
        if length <= 1e-10:
            continue
        direction /= length
        before = np.linalg.norm(result[i] - result[i - 1])
        after = np.linalg.norm(result[i + 1] - result[i])
        result[i - 1] = result[i] - direction * before
        result[i + 1] = result[i] + direction * after
    return result


def _regularize_stroke(stroke: dict, guide: dict | None) -> tuple[dict, dict]:
    stations = np.asarray(stroke['geometry']['stations'], dtype=float)
    centres = stations.mean(axis=1)
    count = len(stations)
    progress = _progress(centres)
    authored_corners = list(stroke['geometry']['corners'])
    inferred_turns: list[int] = []
    target = centres
    breaks: list[int] | None = None
    guide_used = guide is not None
    if guide is not None:
        guide_centres = np.asarray(guide['geometry']['stations'], dtype=float).mean(axis=1)
        guide_centres = _resample(guide_centres, count)
        g0, g1 = guide_centres[0], guide_centres[-1]
        t0, t1 = centres[0], centres[-1]
        gv, tv = g1 - g0, t1 - t0
        if np.linalg.norm(gv) > 1e-10 and np.linalg.norm(tv) > 1e-10:
            scale = np.linalg.norm(tv) / np.linalg.norm(gv)
            angle = np.arctan2(tv[1], tv[0]) - np.arctan2(gv[1], gv[0])
            rotation = np.array([
                [np.cos(angle), -np.sin(angle)],
                [np.sin(angle), np.cos(angle)],
            ])
            aligned = (guide_centres - g0) @ rotation.T * scale + t0
            inferred_turns = _infer_turns(aligned, progress)
            breaks = sorted(set([0, count - 1] + authored_corners + inferred_turns))
            robust_centres = _limit_center_prickles(centres, breaks)
            target = aligned + (1.0 - GUIDE_WEIGHT) * _piecewise_fit(robust_centres - aligned, breaks, progress)
    if breaks is None:
        inferred_turns = [] if authored_corners else _infer_turns(centres, progress)
        breaks = sorted(set([0, count - 1] + authored_corners + inferred_turns))
        target = _limit_center_prickles(centres, breaks)
    regular_centres = _piecewise_fit(target, breaks, progress)
    regular_centres = _join_inferred_turns(regular_centres, inferred_turns)
    regular_centres = _keep_centres_bounded(regular_centres, centres)
    tangents = _tangents(regular_centres, breaks)
    normals = np.column_stack([-tangents[:, 1], tangents[:, 0]])
    pair_vectors = stations[:, 0] - stations[:, 1]
    raw_left = np.sum((stations[:, 0] - centres) * normals, axis=1)
    if np.count_nonzero(raw_left >= 0) < count / 2:
        normals *= -1
    widths = np.abs(np.sum(pair_vectors * normals, axis=1))
    robust_width = widths.copy()
    for i in range(1, count - 1):
        neighbour = max(widths[i - 1] + widths[i + 1], 1e-8) / 2.0
        if widths[i] > SPIKE_RATIO * neighbour:
            if i in breaks:
                continue
            robust_width[i] = SPIKE_RATIO * neighbour
    regular_width = _width_fit(robust_width, progress, breaks)
    left_dist = np.maximum(np.sum((stations[:, 0] - centres) * normals, axis=1), 0.0)
    fraction = np.divide(left_dist, widths, out=np.full(count, 0.5), where=widths > 1e-10)
    fraction = np.clip(_width_fit(fraction, progress, breaks), 0.15, 0.85)
    left = regular_width * fraction
    right = regular_width - left
    left = np.minimum(left, _ray_limit(regular_centres, normals))
    right = np.minimum(right, _ray_limit(regular_centres, -normals))
    contacts = np.stack([
        regular_centres + normals * left[:, None],
        regular_centres - normals * right[:, None],
    ], axis=1)
    result = copy.deepcopy(stroke)
    result['geometry']['stations'] = contacts.tolist()
    displacement = np.linalg.norm(regular_centres - centres, axis=1)
    new_width = left + right
    delta = np.diff(regular_centres, axis=0)
    segment = np.linalg.norm(delta, axis=1)
    angles = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
    local_curvature = np.abs(np.diff(angles)) / np.maximum((segment[:-1] + segment[1:]) / 2, 1e-10)
    curvature_width = local_curvature * new_width[1:-1] / 2 if len(new_width) > 2 else np.array([0.0])
    report = {
        'id': stroke['id'],
        'stations': count,
        'cubicSpans': len(breaks) - 1,
        'guideUsed': guide_used,
        'spikesLimited': int(np.count_nonzero(robust_width != widths)),
        'authoredCorners': authored_corners,
        'inferredTurns': inferred_turns,
        'centerDisplacementMean': float(displacement.mean()),
        'centerDisplacementMax': float(displacement.max()),
        'centerRetention': float(1.0 - np.clip(displacement.mean() / max(np.ptp(centres, axis=0).max(), 1e-12), 0, 1)),
        'curvatureBefore': _curvature(centres),
        'curvatureAfter': _curvature(regular_centres),
        'curvatureChange': _curvature(regular_centres) - _curvature(centres),
        'widthChangeMean': float(np.mean(np.abs(new_width - widths))),
        'widthRoughnessBefore': _roughness(widths),
        'widthRoughnessAfter': _roughness(new_width),
        'maximumCurvatureHalfWidth': float(np.max(curvature_width)),
        'minimumBoundMargin': float(np.min(np.minimum(contacts, 1.0 - contacts))),
    }
    return result, report


def regularize_program(program: Any, guide_program: Any | None = None) -> tuple[dict, dict]:
    """Return a regularized deep copy of an IR 0.2 program and measurements."""
    validate_program(program)
    if program['schemaVersion'] != SCHEMA_VERSION:
        raise ValueError('stroke regularization requires kai-stroke-ir/0.2')
    guides: dict[str, dict] = {}
    if guide_program is not None:
        validate_program(guide_program)
        if guide_program['schemaVersion'] != SCHEMA_VERSION:
            raise ValueError('guide regularization requires kai-stroke-ir/0.2')
        guides = {stroke['id']: stroke for stroke in guide_program['strokes']}
    output = copy.deepcopy(program)
    reports = []
    for index, stroke in enumerate(program['strokes']):
        item, r = _regularize_stroke(stroke, guides.get(stroke['id']))
        output['strokes'][index] = item
        reports.append(r)
    validate_program(output)
    report = {
        'method': METHOD,
        'claim': 'experimental geometric regularizer; not a physical brush simulation',
        'config': {
            'guideWeight': GUIDE_WEIGHT,
            'ridge': RIDGE,
            'spikeRatio': SPIKE_RATIO,
            'boundEpsilon': BOUND_EPSILON,
            'maximumPolynomialDegreePerSpan': 3,
            'maximumCubicSpans': MAX_CUBIC_SPANS,
            'minimumTurnSeparation': MIN_TURN_SEPARATION,
            'turnThresholdRadians': float(TURN_THRESHOLD_RADIANS),
            'widthProgressKnots': [0, 0.08, 0.25, 0.5, 0.75, 0.92, 1],
        },
        'strokes': reports,
        'aggregate': {
            'centerDisplacementMean': float(np.mean([r['centerDisplacementMean'] for r in reports])),
            'curvatureChangeMean': float(np.mean([r['curvatureChange'] for r in reports])),
            'widthChangeMean': float(np.mean([r['widthChangeMean'] for r in reports])),
            'centerRetentionMean': float(np.mean([r['centerRetention'] for r in reports])),
        },
    }
    return output, report


__all__ = ["regularize_program"]
