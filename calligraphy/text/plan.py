"""Geometry-independent page and timing contract for current/future renderers."""
import math
from typing import Dict, Any, Optional

from .input import parse_text
from .layout import layout_text, _finite_number, _positive_integer


def _positive_number(value, name: str, maximum: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TypeError(f"{name} must be a number > 0")
    val = float(value)
    if val <= 0 or val > maximum:
        raise ValueError(f"{name} must be in (0, {maximum}]")
    return val


def create_text_plan(
    text: str,
    stroke_counts: Dict[str, int],
    layout: Optional[Dict[str, Any]] = None,
    timing: Optional[Dict[str, Any]] = None,
    punctuation: str = "break",
) -> Dict[str, Any]:
    """Create a timing and placement plan (schemaVersion 1)."""
    parsed = parse_text(text, punctuation=punctuation)
    if not isinstance(stroke_counts, dict):
        raise TypeError("strokeCounts must map each character to a positive stroke count")

    missing = [c for c in parsed["uniqueCharacters"] if c not in stroke_counts]
    if missing:
        raise ValueError(f"Missing stroke counts: {' '.join(missing)}")

    counts = {}
    for character in parsed["uniqueCharacters"]:
        count = _positive_integer(stroke_counts[character], f"stroke count for {character}", minimum=1)
        if count > 128:
            raise ValueError(f"Stroke count for {character} exceeds 128")
        counts[character] = count

    layout = layout or {}
    layout_args = {}
    if "width" in layout:
        layout_args["width"] = layout["width"]
    if "height" in layout:
        layout_args["height"] = layout["height"]
    if "direction" in layout:
        layout_args["direction"] = layout["direction"]
    if "charactersPerLine" in layout:
        layout_args["characters_per_line"] = layout["charactersPerLine"]
    elif "characters_per_line" in layout:
        layout_args["characters_per_line"] = layout["characters_per_line"]
    if "margin" in layout:
        layout_args["margin"] = layout["margin"]
    if "gap" in layout:
        layout_args["gap"] = layout["gap"]

    for name in ("font_size", "fit"):
        if name in layout:
            layout_args[name] = layout[name]

    page = layout_text(parsed["lines"], **layout_args)

    timing = timing or {}
    intro = _finite_number(timing.get("intro", 0.5), "intro", minimum=0, maximum=60)
    outro = _finite_number(timing.get("outro", 1.0), "outro", minimum=0, maximum=60)
    gap = _finite_number(
        timing.get("characterGap", timing.get("character_gap", 0.15)),
        "characterGap",
        minimum=0,
        maximum=60,
    )
    stroke_seconds = _positive_number(
        timing.get("strokeSeconds", timing.get("stroke_seconds", 0.18)),
        "strokeSeconds",
        maximum=60,
    )

    cursor = intro
    schedule = []
    num_placements = len(page["placements"])
    for index, placement in enumerate(page["placements"]):
        stroke_count = counts[placement["character"]]
        duration = stroke_count * stroke_seconds
        entry = {
            **placement,
            "index": index,
            "strokeCount": stroke_count,
            "start": cursor,
            "duration": duration,
            "end": cursor + duration,
        }
        schedule.append(entry)
        cursor += duration + (gap if index < num_placements - 1 else 0)

    total_duration = cursor + outro
    return {
        "schemaVersion": 1,
        "text": text,
        "width": page["width"],
        "height": page["height"],
        "direction": page["direction"],
        "strokeSeconds": stroke_seconds,
        "duration": total_duration,
        "schedule": schedule,
        "omitted": parsed["omitted"],
    }
