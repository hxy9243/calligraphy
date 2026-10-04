"""Fit a target stroke with paired boundary contacts for ``ContactBrush``.

This is a bounded silhouette fitter, not historical brush-motion recovery.
The target is represented by two ordered contour rails running from the guide's
entry end to its exit end.  Increasingly dense, arc-length-spaced station pairs
are tried (12--64); a 97.5% adaptive margin is sought and 95% is required.
"""

from __future__ import annotations

import cv2
import numpy as np

from .brush_grammar import ContactBrush
from .engine_metadata import engine_metadata
from .rail_alignment import _arc_resample, align_rails


def _path(contour: np.ndarray, first: int, last: int, step: int) -> np.ndarray:
    n = len(contour)
    indices = [first]
    while indices[-1] != last:
        indices.append((indices[-1] + step) % n)
    return contour[indices]


def _iou(candidate: np.ndarray, target: np.ndarray) -> float:
    candidate = candidate > 0.5
    intersection = np.count_nonzero(candidate & target)
    return float(intersection / max(np.count_nonzero(candidate | target), 1))


def _connected(mask: np.ndarray) -> bool:
    count, _ = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    return count == 2  # background plus one deposited component


def _motion_checks(brush: dict) -> dict:
    painter = ContactBrush(brush, size=480)
    frames = [painter.advance(float(t)) > 0.5 for t in np.linspace(0, 1, 31)]
    monotonic = all(np.all(a <= b) for a, b in zip(frames, frames[1:]))
    # Connectivity uses deposited support (>0), because anti-aliased edge
    # pixels below the silhouette threshold can be the only bridge at a tip.
    support_painter = ContactBrush(brush, size=480)
    supports = [support_painter.advance(float(t)) > 0 for t in np.linspace(0, 1, 31)]
    connected = all(not frame.any() or _connected(frame) for frame in supports)
    # The final two contact spans are the terminal region.  They must remain
    # absent at the midpoint, rather than being prepainted and merely revealed.
    tail = dict(brush)
    contacts = np.asarray(brush["contacts"])
    tail_count = 3
    # Tiny dots can have less than one pixel of midpoint travel in their last
    # two spans. Extend the diagnostic tail until it is a valid engine gesture.
    while (tail_count < len(contacts) and
           np.linalg.norm(np.diff(contacts[-tail_count:].mean(axis=1), axis=0), axis=1).sum() < 1):
        tail_count += 1
    tail["contacts"] = contacts[-tail_count:].tolist()
    tail_start = len(contacts) - tail_count
    tail["corners"] = [k - tail_start for k in brush.get("corners", []) if k >= tail_start]
    tail["features"] = [{**f, "station": f["station"] - tail_start}
                        for f in brush.get("features", []) if f["station"] >= tail_start]
    terminal = ContactBrush(tail, size=480).advance(1.0) > 0.5
    future_hidden = not np.any(frames[15] & terminal)
    return {"prefixFrames": 31, "monotonic": monotonic,
            "prefixConnected": connected, "futureTerminalHiddenAtHalf": future_hidden}


def fit_contact_stroke(target480: np.ndarray, guide_nx2: np.ndarray,
                       target_iou: float = 0.975) -> dict:
    """Return normalized and 480px paired contacts plus a measured fit report.

    ``guide_nx2`` is ordered entry-to-exit in unit-square coordinates.  No
    target pixels are copied into the rendering: the result is deposited by the
    installed :class:`ContactBrush` from at most 64 paired contact stations.
    """
    if not np.isfinite(target_iou) or not 0.95 <= target_iou <= 1:
        raise ValueError("target_iou must be finite in [.95,1]")
    target = np.asarray(target480, dtype=bool)
    guide = np.asarray(guide_nx2, dtype=float)
    if target.shape != (480, 480):
        raise ValueError("target480 must have shape (480, 480)")
    if guide.ndim != 2 or guide.shape[1] != 2 or len(guide) < 2:
        raise ValueError("guide_nx2 must contain at least two [x,y] points")
    if not np.isfinite(guide).all() or np.any((guide < 0) | (guide > 1)):
        raise ValueError("guide_nx2 must be finite and normalized to 0..1")

    component_count, _ = cv2.connectedComponents(target.astype(np.uint8), connectivity=8)
    contours_all, hierarchy = cv2.findContours(target.astype(np.uint8), cv2.RETR_CCOMP,
                                                cv2.CHAIN_APPROX_NONE)
    if component_count != 2:
        raise ValueError("target480 must contain exactly one connected ink component")
    if hierarchy is not None and any(row[3] >= 0 for row in hierarchy[0]):
        raise ValueError("target480 holes are not supported by a two-rail contact stroke")
    contours = [c for c, row in zip(contours_all, hierarchy[0]) if row[3] < 0]
    if not contours:
        raise ValueError("target480 contains no ink")
    contour = max(contours, key=cv2.contourArea)[:, 0, :].astype(float)
    # OpenCV returns centers of boundary pixels, whereas contact rails delimit
    # ink area. Move outward by a shared subpixel offset before interpolation;
    # otherwise thin strokes systematically lose their boundary pixels. The
    # 1/3px offset matches one supersample in ContactBrush's 3x rasterizer.
    tangent = np.roll(contour, -2, axis=0) - np.roll(contour, 2, axis=0)
    outward = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    outward /= np.maximum(np.linalg.norm(outward, axis=1)[:, None], 1e-9)
    if cv2.contourArea(contour.astype(np.float32), oriented=True) > 0:
        outward *= -1
    contour = contour + outward / 3.0
    endpoints = guide[[0, -1]] * 480.0
    start = int(np.argmin(np.sum((contour - endpoints[0]) ** 2, axis=1)))
    end = int(np.argmin(np.sum((contour - endpoints[1]) ** 2, axis=1)))
    if start == end:
        raise ValueError("guide entry and exit resolve to the same boundary point")

    forward = _path(contour, start, end, 1)
    backward = _path(contour, start, end, -1)
    best = None
    trials = []
    for stations in range(12, 65, 4):
        a, b = _arc_resample(forward, stations), _arc_resample(backward, stations)
        contacts480 = np.stack([a, b], axis=1)
        # Zero tension makes each rail span trace its contour chord without
        # overshoot; ContactBrush still performs its normal strip deposition.
        brush = {"contacts": contacts480.tolist(), "corners": [], "tension": 0.0}
        rendered = ContactBrush(brush, size=480).advance(1.0)
        score = _iou(rendered, target)
        trial = {"stations": stations, "iou480": score,
                 "connected": _connected(rendered > 0.5)}
        trials.append(trial)
        if trial["connected"] and (best is None or score > best[0]):
            best = (score, contacts480, rendered, stations)
        if score >= target_iou and trial["connected"]:
            break

    correspondence = "equal arc length"
    # Concave turns can require unequal progress on the two rails. Keep the
    # simple candidate when it clears the gate; otherwise align locally inside
    # the known target. The exported renderer still sees only contact geometry.
    if best is None or best[0] < 0.95:
        contacts480 = align_rails(forward, backward, target, guide)
        brush = {"contacts": contacts480.tolist(), "corners": [], "tension": 0.0}
        rendered = ContactBrush(brush, size=480).advance(1.0)
        score = _iou(rendered, target)
        connected = _connected(rendered > 0.5)
        trials.append({"stations": len(contacts480), "iou480": score,
                       "connected": connected, "correspondence": "monotone alignment"})
        if connected and (best is None or score > best[0]):
            best = (score, contacts480, rendered, len(contacts480))
            correspondence = "monotone alignment"

    if best is None:
        raise ValueError("no connected contact fit found within station budget")
    score, contacts480, rendered, stations = best
    normalized = np.clip(contacts480 / 480.0, 0.0, 1.0)
    # Verify the public normalized representation, not an unreturned private
    # geometry, is what achieves the reported score.
    public_brush = {"contacts": (normalized * 480.0).tolist(), "corners": [], "tension": 0.0}
    public_render = ContactBrush(public_brush, size=480).advance(1.0)
    score = _iou(public_render, target)
    motion = _motion_checks(public_brush)
    contacts480 = normalized * 480.0
    return {
        "contacts": normalized.tolist(),
        "contacts480": contacts480.tolist(),
        "corners": [],
        "tension": 0.0,
        "report": {
            "engine": engine_metadata('kai-fitted'),
            "algorithm": "subpixel boundary correction; ordered contour split; paired arc-length rails; adaptive 12..64 stations",
            "boundaryOffset480": 1 / 3,
            "correspondence": correspondence,
            "stations": stations,
            "maxContactWidth480": float(np.linalg.norm(contacts480[:, 1] - contacts480[:, 0], axis=1).max()),
            "iou480": score,
            "requiredIou": 0.95,
            "targetReached": bool(score >= 0.95),
            "marginIou": float(target_iou),
            "marginReached": bool(score >= target_iou),
            "connected": _connected(public_render > 0.5),
            **motion,
            "trials": trials,
        },
    }
