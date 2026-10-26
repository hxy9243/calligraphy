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
    inscription: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a timing and placement plan (schemaVersion 1)."""
    parsed = parse_text(text, punctuation=punctuation)
    if not isinstance(stroke_counts, dict):
        raise TypeError("strokeCounts must map each character to a positive stroke count")

    parsed_insc = parse_text(inscription, punctuation=punctuation) if (inscription and inscription.strip()) else None
    insc_chars = parsed_insc["uniqueCharacters"] if parsed_insc else []
    all_unique = list(dict.fromkeys(parsed["uniqueCharacters"] + insc_chars))

    missing = [c for c in all_unique if c not in stroke_counts]
    if missing:
        raise ValueError(f"Missing stroke counts: {' '.join(missing)}")

    counts = {}
    for character in all_unique:
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

    for name in ("font_size", "fit", "zigzag"):
        if name in layout:
            layout_args[name] = layout[name]

    page = layout_text(
        parsed["lines"],
        inscription_lines=parsed_insc["lines"] if parsed_insc else None,
        **layout_args,
    )

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

    # Split placements into main text and inscription
    main_placements = [p for p in page["placements"] if not p.get("is_inscription")]
    insc_placements = [p for p in page["placements"] if p.get("is_inscription")]

    num_main = len(main_placements)
    for index, placement in enumerate(main_placements):
        stroke_count = counts[placement["character"]]
        duration = stroke_count * stroke_seconds
        entry = {
            **placement,
            "index": index,
            "strokeCount": stroke_count,
            "start": cursor,
            "duration": duration,
            "end": cursor + duration,
            "is_inscription": False,
        }
        schedule.append(entry)
        cursor += duration + (gap if (index < num_main - 1 or len(insc_placements) > 0) else 0)

    # Inscription characters appear sequentially, one letter each instead of by strokes
    letter_duration = max(0.2, stroke_seconds * 1.5)
    num_insc = len(insc_placements)
    for index, placement in enumerate(insc_placements):
        entry_idx = num_main + index
        entry = {
            **placement,
            "index": entry_idx,
            "strokeCount": counts[placement["character"]],
            "start": cursor,
            "duration": letter_duration,
            "end": cursor + letter_duration,
            "is_inscription": True,
        }
        schedule.append(entry)
        cursor += letter_duration + (gap * 0.6 if index < num_insc - 1 else 0)

    total_duration = cursor + outro
    omitted = parsed["omitted"] + (parsed_insc["omitted"] if parsed_insc else [])

    return {
        "schemaVersion": 1,
        "text": text,
        "inscription": inscription,
        "width": page["width"],
        "height": page["height"],
        "direction": page["direction"],
        "strokeSeconds": stroke_seconds,
        "duration": total_duration,
        "schedule": schedule,
        "omitted": omitted,
    }

