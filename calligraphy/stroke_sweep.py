"""Compile paired contacts to frozen, smooth BrushPainter sweep programs."""

from __future__ import annotations

import copy
import json
import math
from typing import Any

import cv2
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator

from .paint_brush import BrushPainter, fit_brush
from .stroke_ir import BASE_SIZE, SCHEMA_VERSION, render_program, validate_program

SWEEP_SCHEMA_VERSION = "smooth-brush-program/0.1"
MAX_STROKES = 64
MAX_SWEEP_STATIONS = 2048
MAX_PRESSURE_KNOTS = 12
MAX_RADIUS_RATE = 0.5


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _roughness(values: np.ndarray) -> float:
    return float(np.sum(np.abs(np.diff(values, n=2))) / max(float(np.mean(values)), 1e-8)) if len(values) > 2 else 0.0


def _arc(path: np.ndarray) -> np.ndarray:
    return np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]


def _bounded_pressure(path: np.ndarray, raw: np.ndarray) -> np.ndarray:
    """At most twelve positive PCHIP controls with a radius/length rate cap."""
    smooth = ndi.gaussian_filter1d(raw, max(1.0, len(raw) / 80), mode="nearest")
    count = min(MAX_PRESSURE_KNOTS, len(raw))
    knots = np.unique(np.round(np.linspace(0, len(raw) - 1, count)).astype(int))
    radius = PchipInterpolator(knots, smooth[knots])(np.arange(len(raw)))
    distance = np.linalg.norm(np.diff(path, axis=0), axis=1)
    for i in range(1, len(radius)):
        radius[i] = np.clip(radius[i], radius[i-1] - MAX_RADIUS_RATE * distance[i-1],
                            radius[i-1] + MAX_RADIUS_RATE * distance[i-1])
    for i in range(len(radius) - 2, -1, -1):
        radius[i] = np.clip(radius[i], radius[i+1] - MAX_RADIUS_RATE * distance[i],
                            radius[i+1] + MAX_RADIUS_RATE * distance[i])
    return np.maximum(radius, 0.7)


def _isolated(program: dict, stroke: dict) -> dict:
    item = copy.deepcopy(program)
    item["strokes"] = [copy.deepcopy(stroke)]
    item["relations"] = []
    return item


def _compile_stroke(program: dict, stroke: dict) -> tuple[dict, dict]:
    contacts = np.asarray(stroke["geometry"]["stations"], float) * BASE_SIZE
    original_centres = contacts.mean(axis=1)
    direction = original_centres[-1] - original_centres[0]
    layer = render_program(_isolated(program, stroke), 1, BASE_SIZE)
    fallback = False
    try:
        brush = fit_brush(layer, direction)
    except ValueError:
        brush = fit_brush(layer, direction, guide=original_centres)
        fallback = True
    path = np.asarray(brush["path"], float)
    raw_radius = np.asarray(brush["radius"], float)
    body = float(np.percentile(raw_radius, 75))
    keep = np.flatnonzero(raw_radius >= 0.4 * body)
    lo, hi = (int(keep[0]), int(keep[-1]) + 1) if len(keep) else (0, len(path))
    trimmed_start = float(_arc(path[:lo + 1])[-1]) if lo else 0.0
    trimmed_end = float(_arc(path[hi - 1:])[-1]) if hi < len(path) else 0.0
    path, raw_radius = path[lo:hi], raw_radius[lo:hi]
    radius = _bounded_pressure(path, raw_radius)
    arc = _arc(path)
    times = 0.02 + 0.96 * arc / max(float(arc[-1]), 1e-8)
    geometry = {
        "type": "elliptical-sweep", "path": path.tolist(), "radius": radius.tolist(),
        "times": times.tolist(), "nibAspect": float(brush["nib_aspect"]),
        "tailLift": False,
    }
    compiled = {"id": stroke["id"], "kind": stroke["kind"], "duration": stroke["duration"],
                "liftAfter": stroke["liftAfter"], "geometry": geometry}
    old_progress = np.linspace(0, 1, len(original_centres))
    new_progress = arc / max(float(arc[-1]), 1e-8)
    old_at_new = np.column_stack([np.interp(new_progress, old_progress, original_centres[:, a]) for a in range(2)])
    report = {
        "id": stroke["id"], "fallbackGuideUsed": fallback,
        "pressureKnots": min(MAX_PRESSURE_KNOTS, len(raw_radius)),
        "radiusRoughnessBefore": _roughness(raw_radius), "radiusRoughnessAfter": _roughness(radius),
        "widthRoughnessBefore": _roughness(raw_radius * 2), "widthRoughnessAfter": _roughness(radius * 2),
        "centerDisplacementMean": float(np.mean(np.linalg.norm(path - old_at_new, axis=1)) / BASE_SIZE),
        "trimmedStartDistance": trimmed_start / BASE_SIZE, "trimmedEndDistance": trimmed_end / BASE_SIZE,
    }
    return compiled, report


def validate_smooth_program(program: Any) -> Any:
    if not isinstance(program, dict) or set(program) != {"schemaVersion", "character", "script", "provenance", "strokes", "relations"}:
        raise ValueError("smooth program has invalid top-level fields")
    if program["schemaVersion"] != SWEEP_SCHEMA_VERSION or program["script"] != "kai":
        raise ValueError("unsupported smooth brush program")
    if not isinstance(program["character"], str) or len(program["character"]) != 1:
        raise ValueError("smooth program character must be one Unicode character")
    if not isinstance(program["provenance"], dict):
        raise ValueError("smooth program provenance must be an object")
    try:
        json.dumps(program["provenance"], allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"smooth program provenance must be finite JSON ({exc})") from exc
    if not isinstance(program["strokes"], list) or not 1 <= len(program["strokes"]) <= MAX_STROKES:
        raise ValueError("smooth program strokes are invalid")
    ids = set()
    for stroke in program["strokes"]:
        if set(stroke) != {"id", "kind", "duration", "liftAfter", "geometry"}:
            raise ValueError("smooth stroke has invalid fields")
        if not isinstance(stroke["id"], str) or not stroke["id"] or stroke["id"] in ids:
            raise ValueError("smooth stroke id is invalid")
        ids.add(stroke["id"])
        if not _finite(stroke["duration"]) or stroke["duration"] <= 0 or not _finite(stroke["liftAfter"]) or stroke["liftAfter"] < 0:
            raise ValueError("smooth stroke timing is invalid")
        geometry = stroke["geometry"]
        if set(geometry) != {"type", "path", "radius", "times", "nibAspect", "tailLift"} or geometry["type"] != "elliptical-sweep":
            raise ValueError("smooth stroke geometry is invalid")
        path, radius, times = np.asarray(geometry["path"], float), np.asarray(geometry["radius"], float), np.asarray(geometry["times"], float)
        if not 2 <= len(path) <= MAX_SWEEP_STATIONS or path.shape != (len(radius), 2) or len(times) != len(path):
            raise ValueError("smooth stroke station counts mismatch")
        if not np.isfinite(path).all() or not np.isfinite(radius).all() or not np.isfinite(times).all():
            raise ValueError("smooth stroke geometry must be finite")
        if np.any(path < 0) or np.any(path > BASE_SIZE) or np.any(radius <= 0) or np.any(radius > BASE_SIZE / 2):
            raise ValueError("smooth stroke geometry is out of bounds")
        distance = np.linalg.norm(np.diff(path, axis=0), axis=1)
        if float(distance.sum()) <= 1e-8:
            raise ValueError("smooth stroke path must travel")
        if np.any(np.abs(np.diff(radius)) > MAX_RADIUS_RATE * distance + 1e-6):
            raise ValueError("smooth stroke radius changes too quickly for path length")
        if np.any(np.diff(times) < 0) or times[0] < 0 or times[-1] > 1:
            raise ValueError("smooth stroke times are invalid")
        if not _finite(geometry["nibAspect"]) or not 0 < geometry["nibAspect"] <= 1 or not isinstance(geometry["tailLift"], bool):
            raise ValueError("smooth stroke brush parameters are invalid")
    if not isinstance(program["relations"], list):
        raise ValueError("smooth program relations must be a list")
    for relation in program["relations"]:
        if not isinstance(relation, dict) or relation.get("a") not in ids or relation.get("b") not in ids:
            raise ValueError("smooth program relation is invalid")
    if not math.isfinite(sum(s["duration"] + s["liftAfter"] for s in program["strokes"])):
        raise ValueError("smooth program timeline must be finite")
    return program


def compile_smooth_program(program: Any) -> tuple[dict, dict]:
    validate_program(program)
    if program["schemaVersion"] != SCHEMA_VERSION:
        raise ValueError("smooth sweep compilation requires kai-stroke-ir/0.2")
    output = {"schemaVersion": SWEEP_SCHEMA_VERSION, "character": program["character"], "script": program["script"],
              "provenance": copy.deepcopy(program["provenance"]), "strokes": [], "relations": copy.deepcopy(program["relations"])}
    reports = []
    for stroke in program["strokes"]:
        item, report = _compile_stroke(program, stroke)
        output["strokes"].append(item); reports.append(report)
    validate_smooth_program(output)
    return output, {"method": "isolated-medial-elliptical-sweep/1", "pressureKnotsMaximum": MAX_PRESSURE_KNOTS,
                    "maximumRadiusRate": MAX_RADIUS_RATE, "strokes": reports}


def _painter_geometry(geometry: dict) -> dict:
    return {"path": geometry["path"], "radius": geometry["radius"], "times": geometry["times"],
            "nib_aspect": geometry["nibAspect"], "tail_lift": geometry["tailLift"]}


def render_smooth_program(program: Any, progress: float, size: int = BASE_SIZE) -> np.ndarray:
    validate_smooth_program(program)
    if not _finite(progress) or not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        raise ValueError("progress must be finite and size a positive integer")
    total = sum(s["duration"] + s["liftAfter"] for s in program["strokes"])
    now, start = float(np.clip(progress, 0, 1)) * total, 0.0
    canvas = np.zeros((BASE_SIZE, BASE_SIZE), np.float32)
    for stroke in program["strokes"]:
        local = np.clip((now - start) / stroke["duration"], 0, 1)
        if local > 0:
            canvas = np.maximum(canvas, BrushPainter(_painter_geometry(stroke["geometry"])).advance(float(local)))
        start += stroke["duration"] + stroke["liftAfter"]
    if size != BASE_SIZE:
        canvas = cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA)
    return np.clip(canvas, 0, 1).astype(np.float32, copy=False)


__all__ = ["compile_smooth_program", "render_smooth_program", "validate_smooth_program"]
