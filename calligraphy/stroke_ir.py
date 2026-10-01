"""Experimental, bounded Kai stroke IR compiler and deterministic renderer.

The IR supports cubic centre paths with asymmetric contact widths (0.1), or
bounded explicit paired contact stations (0.2), compiled to records consumed by the
existing :class:`ContactBrush`.  It is not a pressure or bristle model.
"""

from __future__ import annotations

import json
import math
from typing import Any

import cv2
import numpy as np

from .brush_grammar import ContactBrush


SCHEMA_VERSION = "kai-stroke-ir/0.2"
LEGACY_SCHEMA_VERSION = "kai-stroke-ir/0.1"
MAX_CONTACT_STATIONS = 64
BASE_SIZE = 480
MAX_STROKES = 64
MAX_PATH_SEGMENTS = 32
MAX_PROFILE_KNOTS = 64
MAX_CORNERS = 64
REGULAR_STATIONS = 33


def _fail(message: str) -> None:
    raise ValueError(message)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _require_keys(value: dict, required: set[str], optional: set[str], where: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        _fail(f"{where}: missing {', '.join(sorted(missing))}")
    if extra:
        _fail(f"{where}: unknown {', '.join(sorted(extra))}")


def validate_program(program: Any):
    """Validate and return *program* unchanged.

    Errors include the glyph and, once known, stroke identifier so malformed
    authored data can be located without relying on a list index alone.
    """

    if not isinstance(program, dict):
        _fail("glyph <unknown>: program must be an object")
    character = program.get("character", "<unknown>")
    glyph = f"glyph {character!r}"
    _require_keys(
        program,
        {"schemaVersion", "character", "script", "provenance", "strokes", "relations"},
        set(),
        glyph,
    )
    if program["schemaVersion"] not in (LEGACY_SCHEMA_VERSION, SCHEMA_VERSION):
        _fail(f"{glyph}: schemaVersion must be {SCHEMA_VERSION!r}")
    if not isinstance(character, str) or len(character) != 1:
        _fail(f"{glyph}: character must be one Unicode character")
    if program["script"] != "kai":
        _fail(f"{glyph}: script must be 'kai'")
    if not isinstance(program["provenance"], dict):
        _fail(f"{glyph}: provenance must be an object")
    try:
        json.dumps(program["provenance"], allow_nan=False)
    except (TypeError, ValueError) as exc:
        _fail(f"{glyph}: provenance must be finite JSON data ({exc})")

    strokes = program["strokes"]
    if not isinstance(strokes, list) or not strokes or len(strokes) > MAX_STROKES:
        _fail(f"{glyph}: strokes must contain 1..{MAX_STROKES} items")
    ids: set[str] = set()
    for index, stroke in enumerate(strokes):
        if not isinstance(stroke, dict):
            _fail(f"{glyph} stroke #{index + 1}: stroke must be an object")
        stroke_id = stroke.get("id", f"#{index + 1}")
        where = f"{glyph} stroke {stroke_id!r}"
        _require_keys(
            stroke,
            ({"id", "kind", "geometry", "duration", "liftAfter"}
             if program["schemaVersion"] == SCHEMA_VERSION else
             {"id", "kind", "path", "profile", "corners", "duration", "liftAfter"}),
            set(),
            where,
        )
        if not isinstance(stroke_id, str) or not stroke_id:
            _fail(f"{where}: id must be a nonempty string")
        if stroke_id in ids:
            _fail(f"{where}: duplicate stroke id")
        ids.add(stroke_id)
        if not isinstance(stroke["kind"], str) or not stroke["kind"]:
            _fail(f"{where}: kind must be a nonempty string")

        if program["schemaVersion"] == SCHEMA_VERSION:
            geometry = stroke["geometry"]
            if not isinstance(geometry, dict):
                _fail(f"{where}: geometry must be an object")
            _require_keys(geometry, {"type", "stations", "corners", "tension"}, set(), where)
            if geometry["type"] != "paired-contacts":
                _fail(f"{where}: geometry type must be paired-contacts")
            stations = geometry["stations"]
            if not isinstance(stations, list) or not 3 <= len(stations) <= MAX_CONTACT_STATIONS:
                _fail(f"{where}: expected 3..{MAX_CONTACT_STATIONS} contact stations")
            for pair in stations:
                if (not isinstance(pair, list) or len(pair) != 2 or
                    any(not isinstance(point, list) or len(point) != 2 or
                        not all(_finite_number(v) and 0 <= v <= 1 for v in point)
                        for point in pair)):
                    _fail(f"{where}: stations must contain finite unit-square edge pairs")
            a = np.asarray(stations, float)
            if np.linalg.norm(np.diff(a.mean(axis=1), axis=0), axis=1).sum() < 1 / BASE_SIZE:
                _fail(f"{where}: contact trajectory must travel at least one canonical pixel")
            if not np.any(np.linalg.norm(a[:, 1] - a[:, 0], axis=1) > 0):
                _fail(f"{where}: contact geometry must have width")
            corners = geometry["corners"]
            if (not isinstance(corners, list) or any(
                not isinstance(k, int) or isinstance(k, bool) or not 0 <= k < len(a)
                for k in corners) or any(x >= y for x, y in zip(corners, corners[1:]))):
                _fail(f"{where}: contact corner indices must be ordered, unique and in range")
            if not _finite_number(geometry["tension"]) or not 0 <= geometry["tension"] <= 1:
                _fail(f"{where}: contact tension must be in [0,1]")
        else:
            path = stroke["path"]
            if not isinstance(path, list) or not 1 <= len(path) <= MAX_PATH_SEGMENTS:
                _fail(f"{where}: path must contain 1..{MAX_PATH_SEGMENTS} cubic segments")
            previous_end = None
            for segment_index, segment in enumerate(path):
                if not isinstance(segment, list) or len(segment) != 4:
                    _fail(f"{where}: path segment {segment_index} must have four control points")
                for point in segment:
                    if (
                        not isinstance(point, list)
                        or len(point) != 2
                        or not all(_finite_number(v) and 0 <= v <= 1 for v in point)
                    ):
                        _fail(f"{where}: path segment {segment_index} points must be finite [x,y] in [0,1]")
                if previous_end is not None and segment[0] != previous_end:
                    _fail(f"{where}: adjacent cubic segments must share an endpoint")
                previous_end = segment[3]
            path_points = np.asarray(path, float).reshape(-1, 2)
            if np.linalg.norm(np.diff(path_points, axis=0), axis=1).sum() <= 1e-12:
                _fail(f"{where}: path must travel")

            profile = stroke["profile"]
            if not isinstance(profile, list) or not 2 <= len(profile) <= MAX_PROFILE_KNOTS:
                _fail(f"{where}: profile must contain 2..{MAX_PROFILE_KNOTS} knots")
            last_s = -1.0
            for knot_index, knot in enumerate(profile):
                if not isinstance(knot, dict):
                    _fail(f"{where}: profile knot {knot_index} must be an object")
                _require_keys(knot, {"s", "left", "right"}, {"angle"}, f"{where} profile knot {knot_index}")
                if not all(_finite_number(knot.get(k)) for k in ("s", "left", "right")):
                    _fail(f"{where}: profile knot {knot_index} values must be finite numbers")
                if "angle" in knot and not _finite_number(knot["angle"]):
                    _fail(f"{where}: profile knot {knot_index} angle must be finite")
                if not 0 <= knot["s"] <= 1 or knot["s"] <= last_s:
                    _fail(f"{where}: profile s values must be strictly increasing in [0,1]")
                if not 0 <= knot["left"] <= 1 or not 0 <= knot["right"] <= 1:
                    _fail(f"{where}: profile widths must be in [0,1]")
                last_s = knot["s"]
            if profile[0]["s"] != 0 or profile[-1]["s"] != 1:
                _fail(f"{where}: profile must include s=0 and s=1 endpoints")
            if not any(k["left"] + k["right"] > 0 for k in profile):
                _fail(f"{where}: profile must contain a nonzero contact width")

            corners = stroke["corners"]
            if not isinstance(corners, list) or len(corners) > MAX_CORNERS:
                _fail(f"{where}: corners must contain at most {MAX_CORNERS} values")
            if any(not _finite_number(s) or not 0 < s < 1 for s in corners):
                _fail(f"{where}: corners must be finite progress values strictly inside (0,1)")
            if any(a >= b for a, b in zip(corners, corners[1:])):
                _fail(f"{where}: corners must be strictly increasing")
        if not _finite_number(stroke["duration"]) or stroke["duration"] <= 0:
            _fail(f"{where}: duration must be a positive finite number")
        if not _finite_number(stroke["liftAfter"]) or stroke["liftAfter"] < 0:
            _fail(f"{where}: liftAfter must be a nonnegative finite number")

    total_timeline = sum(s["duration"] + s["liftAfter"] for s in strokes)
    if not math.isfinite(total_timeline):
        _fail(f"{glyph}: total stroke timeline must be finite")

    relations = program["relations"]
    if not isinstance(relations, list):
        _fail(f"{glyph}: relations must be a list")
    for index, relation in enumerate(relations):
        where = f"{glyph} relation #{index + 1}"
        if not isinstance(relation, dict):
            _fail(f"{where}: relation must be an object")
        _require_keys(relation, {"kind", "a", "b"}, set(), where)
        if not isinstance(relation["kind"], str) or relation["kind"] not in {"cross", "touch", "near"}:
            _fail(f"{where}: kind must be cross, touch, or near")
        if not isinstance(relation["a"], str) or not isinstance(relation["b"], str):
            _fail(f"{where}: a and b must be stroke id strings")
        if relation["a"] not in ids or relation["b"] not in ids:
            _fail(f"{where}: a and b must reference stroke ids")
        if relation["a"] == relation["b"]:
            _fail(f"{where}: a and b must reference different strokes")
    return program


def _bezier(segment: np.ndarray, t: np.ndarray) -> np.ndarray:
    u = 1 - t
    return (
        u[:, None] ** 3 * segment[0]
        + 3 * u[:, None] ** 2 * t[:, None] * segment[1]
        + 3 * u[:, None] * t[:, None] ** 2 * segment[2]
        + t[:, None] ** 3 * segment[3]
    )


def _path_lut(path: list) -> tuple[np.ndarray, np.ndarray]:
    points = []
    for index, raw in enumerate(path):
        values = _bezier(np.asarray(raw, float), np.linspace(0, 1, 65))
        points.extend(values if index == 0 else values[1:])
    points = np.asarray(points)
    distance = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    if distance[-1] <= 1e-12:
        raise ValueError("path must travel")
    return points, distance / distance[-1]


def _interp(values: list[float], knots: np.ndarray, stations: np.ndarray) -> np.ndarray:
    return np.interp(stations, knots, np.asarray(values, float))


def _compile_stroke(stroke: dict) -> dict:
    if "geometry" in stroke:
        geometry = stroke["geometry"]
        return {"contacts": (np.asarray(geometry["stations"], float) * BASE_SIZE).tolist(),
                "corners": list(geometry["corners"]), "tension": geometry["tension"]}
    points, arc = _path_lut(stroke["path"])
    profile_s = np.asarray([k["s"] for k in stroke["profile"]], float)
    stations = np.unique(
        np.r_[np.linspace(0, 1, REGULAR_STATIONS), profile_s, np.asarray(stroke["corners"], float)]
    )
    centers = np.column_stack(
        [np.interp(stations, arc, points[:, axis]) for axis in range(2)]
    )
    tangent = np.gradient(centers, stations, axis=0)
    length = np.linalg.norm(tangent, axis=1)
    if np.any(length <= 1e-12):
        # Repeated LUT positions can occur around a cusp.  A wider finite
        # difference supplies a stable authored-path direction there.
        for index in np.flatnonzero(length <= 1e-12):
            lo, hi = max(0, index - 1), min(len(centers) - 1, index + 1)
            tangent[index] = centers[hi] - centers[lo]
        length = np.linalg.norm(tangent, axis=1)
    if np.any(length <= 1e-12):
        raise ValueError(f"stroke {stroke['id']!r}: path direction is undefined")
    tangent /= length[:, None]
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    angles = _interp([k.get("angle", 0.0) for k in stroke["profile"]], profile_s, stations)
    c, s = np.cos(angles), np.sin(angles)
    oriented = np.column_stack(
        (normal[:, 0] * c - normal[:, 1] * s, normal[:, 0] * s + normal[:, 1] * c)
    )
    left = _interp([k["left"] for k in stroke["profile"]], profile_s, stations)
    right = _interp([k["right"] for k in stroke["profile"]], profile_s, stations)
    contacts = np.stack((centers + oriented * left[:, None], centers - oriented * right[:, None]), axis=1)
    contacts *= BASE_SIZE
    corner_set = set(stroke["corners"])
    corner_indices = [i for i, value in enumerate(stations) if value in corner_set]
    return {"contacts": contacts.tolist(), "corners": corner_indices, "tension": 0.65}


def compile_program(program: Any) -> list[dict]:
    """Compile a validated IR glyph to existing ``ContactBrush`` records."""

    validate_program(program)
    records = []
    for stroke in program["strokes"]:
        try:
            records.append(_compile_stroke(stroke))
        except ValueError as exc:
            raise ValueError(f"glyph {program['character']!r} stroke {stroke['id']!r}: {exc}") from exc
    return records


def render_program(program: Any, progress: float, size: int = BASE_SIZE) -> np.ndarray:
    """Render a deterministic grayscale mask at normalized glyph ``progress``.

    Stroke durations and lift intervals form one normalized glyph timeline.
    Lift intervals advance time without depositing ink.  Each call constructs
    new painters, so backward and random seeks are equivalent to replay from 0.
    """

    if not _finite_number(progress):
        _fail("progress must be a finite number")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        _fail("size must be a positive integer")
    records = compile_program(program)
    total = sum(s["duration"] + s["liftAfter"] for s in program["strokes"])
    now = float(np.clip(progress, 0, 1)) * total
    canvas = np.zeros((BASE_SIZE, BASE_SIZE), np.float32)
    start = 0.0
    for stroke, record in zip(program["strokes"], records):
        local = np.clip((now - start) / stroke["duration"], 0, 1)
        if local > 0:
            canvas = np.maximum(canvas, ContactBrush(record, size=BASE_SIZE).advance(float(local)))
        start += stroke["duration"] + stroke["liftAfter"]
    if size != BASE_SIZE:
        canvas = cv2.resize(canvas, (size, size), interpolation=cv2.INTER_AREA)
    # OpenCV can overshoot the source range by a few float ulps while reducing.
    # Keep the public grayscale-mask contract exact for downstream thresholding.
    return np.clip(canvas, 0.0, 1.0).astype(np.float32, copy=False)


__all__ = ["compile_program", "render_program", "validate_program"]
