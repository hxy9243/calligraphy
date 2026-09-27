"""Layout Han text onto a single fitted page with explicit lines and wrapping."""
import math
from typing import List, Optional, Dict, Any


def _positive_integer(value, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be an integer >= {minimum}")
    if int(value) != value or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _finite_number(value, name: str, minimum: float = -math.inf, maximum: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TypeError(f"{name} must be a finite number between {minimum} and {maximum}")
    val = float(value)
    if val < minimum or val > maximum:
        raise ValueError(f"{name} must be a finite number between {minimum} and {maximum}")
    return val


def layout_text(
    lines: List[List[str]],
    width: int = 1080,
    height: int = 1440,
    direction: str = "vertical-rl",
    characters_per_line: Optional[int] = None,
    margin: Optional[float] = None,
    gap: float = 0.18,
) -> Dict[str, Any]:
    """Fit lines of characters into page cell placements.
    
    Returns:
      dict with width, height, direction, charactersPerLine, columns, rows, placements.
    """
    width = _positive_integer(width, "width", minimum=64)
    height = _positive_integer(height, "height", minimum=64)
    if width > 8192 or height > 8192:
        raise ValueError("Page dimensions must not exceed 8192")
    if direction not in ("vertical-rl", "horizontal-lr"):
        raise ValueError("direction must be vertical-rl or horizontal-lr")

    if margin is None:
        margin = min(width, height) * 0.07
    else:
        margin = _finite_number(margin, "margin", minimum=0)
    gap = _finite_number(gap, "gap", minimum=0, maximum=2)

    available_width = width - margin * 2
    available_height = height - margin * 2
    if available_width <= 0 or available_height <= 0:
        raise ValueError("Margins leave no space for writing")

    vertical = direction == "vertical-rl"
    count = sum(len(line) for line in lines)
    if count == 0:
        raise ValueError("No characters to lay out")

    if characters_per_line is None:
        if len(lines) > 1:
            per_line = max(len(line) for line in lines)
        else:
            ratio = (available_height / available_width) if vertical else (available_width / available_height)
            per_line = max(1, math.ceil(math.sqrt(count * ratio)))
    else:
        per_line = _positive_integer(characters_per_line, "charactersPerLine", minimum=1)

    wrapped = []
    for line in lines:
        for idx in range(0, max(1, len(line)), per_line):
            chunk = line[idx : idx + per_line]
            if chunk:
                wrapped.append(chunk)

    longest = max(len(chunk) for chunk in wrapped)
    columns = len(wrapped) if vertical else longest
    rows = longest if vertical else len(wrapped)

    col_denom = columns + (columns - 1) * gap
    row_denom = rows + (rows - 1) * gap
    cell = min(available_width / col_denom, available_height / row_denom)
    if cell < 16:
        raise ValueError("Text is too dense for this page; use a larger page or fewer characters")

    left = (width - cell * col_denom) / 2
    top = (height - cell * row_denom) / 2

    placements = []
    for line_index, line in enumerate(wrapped):
        for index, character in enumerate(line):
            col = (columns - 1 - line_index) if vertical else index
            row = index if vertical else line_index
            x = left + col * cell * (1 + gap)
            y = top + row * cell * (1 + gap)
            placements.append(
                {
                    "character": character,
                    "line": line_index,
                    "column": col,
                    "row": row,
                    "x": x,
                    "y": y,
                    "size": cell,
                }
            )

    return {
        "width": width,
        "height": height,
        "direction": direction,
        "charactersPerLine": per_line,
        "columns": columns,
        "rows": rows,
        "placements": placements,
    }
