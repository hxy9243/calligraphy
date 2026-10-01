"""Monotone correspondence between the two contact rails.

This helper supports the bounded stroke fitter. It uses the known
outline, mask, and source median; it does not infer or generate new strokes.
"""

from __future__ import annotations

import numpy as np


DEFAULT_DENSE_SAMPLES = 128
DEFAULT_OUTSIDE_WEIGHT = 6.0


def _arc_resample(points: np.ndarray, count: int) -> np.ndarray:
    points = np.asarray(points, float)
    keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-7]
    points = points[keep]
    if len(points) < 2:
        raise ValueError("a contour rail must travel")
    distance = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    wanted = np.linspace(0.0, distance[-1], count)
    return np.column_stack([np.interp(wanted, distance, points[:, k]) for k in range(2)])


def _guide_samples(guide: np.ndarray, count: int = 256) -> np.ndarray:
    return _arc_resample(guide * 480.0, count)


def _node_costs(a: np.ndarray, b: np.ndarray, target: np.ndarray,
                guide: np.ndarray, outside_weight: float, guide_weight: float,
                width_weight: float) -> np.ndarray:
    # Interior chord samples reveal pairings that cut across white concavities.
    t = np.linspace(0.08, 0.92, 15)
    chords = a[:, None, None, :] * (1 - t[None, None, :, None]) + b[None, :, None, :] * t[None, None, :, None]
    xy = np.rint(chords).astype(int)
    valid = ((xy[..., 0] >= 0) & (xy[..., 0] < 480) &
             (xy[..., 1] >= 0) & (xy[..., 1] < 480))
    inside = np.zeros(valid.shape, bool)
    inside[valid] = target[xy[..., 1][valid], xy[..., 0][valid]]
    outside = 1.0 - inside.mean(axis=2)

    midpoint = (a[:, None, :] + b[None, :, :]) / 2
    guide_samples = _guide_samples(guide)
    guide_d2 = np.min(np.sum((midpoint[:, :, None, :] - guide_samples[None, None, :, :]) ** 2,
                             axis=3), axis=2)
    width = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    # Progress regularization is intentionally weak: unequal rail progress is
    # the behavior this prototype needs to allow around folds and hooks.
    progress = np.abs(np.linspace(0, 1, len(a))[:, None] - np.linspace(0, 1, len(b))[None, :])
    return (outside_weight * outside + guide_weight * guide_d2 / (480.0 ** 2) +
            width_weight * (width / 480.0) ** 2 + 0.04 * progress)


def _monotone_pairs(cost: np.ndarray) -> np.ndarray:
    n, m = cost.shape
    total = np.full((n, m), np.inf)
    previous = np.full((n, m, 2), -1, dtype=np.int16)
    total[0, 0] = cost[0, 0]
    for i in range(n):
        for j in range(m):
            if i == 0 and j == 0:
                continue
            choices = []
            if i: choices.append((total[i - 1, j], i - 1, j))
            if j: choices.append((total[i, j - 1], i, j - 1))
            if i and j: choices.append((total[i - 1, j - 1], i - 1, j - 1))
            value, pi, pj = min(choices)
            total[i, j] = value + cost[i, j]
            previous[i, j] = (pi, pj)
    path = []
    i, j = n - 1, m - 1
    while i >= 0:
        path.append((i, j))
        if i == 0 and j == 0:
            break
        i, j = map(int, previous[i, j])
    return np.asarray(path[::-1], dtype=int)


def _simplify(points: np.ndarray, maximum: int) -> np.ndarray:
    """Greedily retain the point with greatest 4-D chord interpolation error."""
    keep = [0, len(points) - 1]
    while len(keep) < maximum:
        keep.sort()
        best = (-1.0, None)
        for left, right in zip(keep[:-1], keep[1:]):
            if right <= left + 1:
                continue
            span = np.arange(left + 1, right)
            alpha = ((span - left) / (right - left))[:, None]
            interpolation = points[left] * (1 - alpha) + points[right] * alpha
            error = np.max(np.linalg.norm((points[span] - interpolation).reshape(-1, 2, 2), axis=2), axis=1)
            k = int(np.argmax(error))
            if error[k] > best[0]:
                best = (float(error[k]), int(span[k]))
        if best[1] is None:
            break
        keep.append(best[1])
    return points[sorted(keep)]


def align_rails(forward: np.ndarray, backward: np.ndarray, target480: np.ndarray,
                guide_nx2: np.ndarray, dense: int = DEFAULT_DENSE_SAMPLES,
                stations: int = 64, outside_weight: float = DEFAULT_OUTSIDE_WEIGHT,
                guide_weight: float = 2.0, width_weight: float = 0.4) -> np.ndarray:
    """Return at most ``stations`` paired contacts for supplied corrected rails.

    The rails are 480px contour coordinates ordered entry-to-exit.  The guide
    uses normalized unit-square coordinates.  Correspondence may advance one
    rail without advancing the other, which avoids chords across concavities.
    """
    target = np.asarray(target480, dtype=bool)
    guide = np.asarray(guide_nx2, dtype=float)
    if target.shape != (480, 480):
        raise ValueError("target480 must have shape (480, 480)")
    if guide.ndim != 2 or guide.shape[1] != 2 or len(guide) < 2:
        raise ValueError("guide_nx2 must contain at least two [x,y] points")
    if not 3 <= stations <= 64:
        raise ValueError("stations must be in [3,64]")
    a, b = _arc_resample(forward, dense), _arc_resample(backward, dense)
    cost = _node_costs(a, b, target, guide, outside_weight, guide_weight, width_weight)
    indices = _monotone_pairs(cost)
    paired = np.stack([a[indices[:, 0]], b[indices[:, 1]]], axis=1)
    return _simplify(paired.reshape(len(paired), 4), stations).reshape(-1, 2, 2)

