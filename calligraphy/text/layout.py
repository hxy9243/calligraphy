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


def _pseudo_rand(i: int, j: int = 0) -> float:
    """Deterministic integer hash returning a float in [-1.0, 1.0]."""
    n = (i * 374761393 + j * 668265263 + 1013904223) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = n ^ (n >> 16)
    return (n / 2147483647.5) - 1.0


def layout_text(
    lines: List[List[str]],
    width: int = 1080,
    height: int = 1440,
    direction: str = "vertical-rl",
    characters_per_line: Optional[int] = None,
    margin: Optional[float] = None,
    gap: float = 0.18,
    font_size: Optional[float] = None,
    fit: bool = True,
    zigzag: bool = False,
    inscription_lines: Optional[List[List[str]]] = None,
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

    if font_size is not None:
        font_size = _finite_number(font_size, "font_size", minimum=8, maximum=8192)
    if not isinstance(fit, bool):
        raise TypeError("fit must be a boolean")
    if not isinstance(zigzag, bool):
        raise TypeError("zigzag must be a boolean")

    vertical = direction == "vertical-rl"
    count = sum(len(line) for line in lines)
    if count == 0:
        raise ValueError("No characters to lay out")

    if characters_per_line is None:
        if font_size is not None or len(lines) > 1:
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

    clean_insc_lines = [l for l in inscription_lines if l] if inscription_lines else []
    has_insc = len(clean_insc_lines) > 0
    scale_ratio = 0.5
    num_insc_cols = len(clean_insc_lines) if has_insc else 0
    longest_insc = max((len(l) for l in clean_insc_lines), default=0)

    if vertical:
        main_col_units = columns + (columns - 1) * gap
        inter_section_gap_units = (0.8 + 0.5 * gap) if num_insc_cols > 0 else 0.0
        insc_col_units = scale_ratio * (num_insc_cols + (num_insc_cols - 1) * gap) if num_insc_cols > 0 else 0.0
        base_col_denom = main_col_units + inter_section_gap_units + insc_col_units
        insc_row_units = scale_ratio * (longest_insc * (1 + gap)) + 0.5 if has_insc else 0.0
        base_row_denom = max(rows + (rows - 1) * gap, insc_row_units)

        zigzag_pad = 0.52 if (zigzag and count > 1) else 0.0
        col_denom = base_col_denom
        row_denom = base_row_denom + zigzag_pad

        cell = min(available_width / col_denom, available_height / row_denom)
        if font_size is not None:
            if not fit and font_size > min(available_width / base_col_denom, available_height / base_row_denom) + 1e-6:
                raise ValueError("文字超出畫布，請開啟自動適應、縮小字號或加大畫布 / Text exceeds the canvas; enable fit, reduce font size or enlarge the canvas")
            cell = min(font_size, cell) if fit else font_size
        if cell < (8 if font_size is not None else 16):
            raise ValueError("Text is too dense for this page; use a larger page or fewer characters")

        s = cell * scale_ratio
        total_w = cell * base_col_denom
        left = (width - total_w) / 2
        top = (height - cell * base_row_denom) / 2

        slack_along = max(0.0, available_height - cell * base_row_denom)
        amp_along = min(cell * 0.35, slack_along * 0.52) if (zigzag and count > 1) else 0.0


        if zigzag and len(wrapped) > 1:
            raw_offsets = [_pseudo_rand(idx + 1) for idx in range(len(wrapped))]
            mean_offset = sum(raw_offsets) / len(raw_offsets)
            centered = [r - mean_offset for r in raw_offsets]
            max_abs = max(abs(x) for x in centered) or 1.0
            norm_line_offsets = [x / max_abs for x in centered]
        else:
            norm_line_offsets = [0.0] * max(1, len(wrapped))

        placements = []
        for line_index, line in enumerate(wrapped):
            col_x = left + total_w - cell - line_index * cell * (1 + gap)
            for index, character in enumerate(line):
                col = columns - 1 - line_index
                row = index
                x = col_x
                y = top + row * cell * (1 + gap)
                if amp_along > 0.0:
                    line_stagger = norm_line_offsets[line_index] * amp_along
                    char_jitter = _pseudo_rand(line_index + 1, index + 1) * (cell * 0.09)
                    shift_along = line_stagger + char_jitter
                    shift_across = _pseudo_rand(line_index + 101, index + 1) * min(cell * 0.05, cell * gap * 0.32)
                    y = max(margin, min(height - margin - cell, y + shift_along))
                    x = max(margin, min(width - margin - cell, x + shift_across))
                placements.append(
                    {
                        "character": character,
                        "line": line_index,
                        "column": col,
                        "row": row,
                        "x": x,
                        "y": y,
                        "size": cell,
                        "is_inscription": False,
                    }
                )

        if has_insc:
            for insc_col_idx, line in enumerate(clean_insc_lines):
                col_x = left + (num_insc_cols - 1 - insc_col_idx) * s * (1 + gap)
                total_insc_height = len(line) * s * (1 + gap) - s * gap
                y_offset = min(cell * 0.4, max(0.0, cell * base_row_denom - total_insc_height - s))
                col_y_start = top + y_offset

                for char_idx, character in enumerate(line):
                    placements.append(
                        {
                            "character": character,
                            "line": len(wrapped) + insc_col_idx,
                            "column": -1 - insc_col_idx,
                            "row": char_idx,
                            "x": col_x,
                            "y": col_y_start + char_idx * s * (1 + gap),
                            "size": s,
                            "is_inscription": True,
                        }
                    )

    else:
        num_insc_rows = len(clean_insc_lines) if has_insc else 0
        longest_insc_chars = longest_insc

        main_col_units = columns + (columns - 1) * gap
        main_row_units = rows + (rows - 1) * gap
        insc_row_units = scale_ratio * (num_insc_rows + (num_insc_rows - 1) * gap) if num_insc_rows > 0 else 0.0
        base_row_denom = main_row_units + (0.6 + insc_row_units if num_insc_rows > 0 else 0.0)

        insc_col_units = scale_ratio * (longest_insc_chars + (longest_insc_chars - 1) * gap)
        base_col_denom = max(main_col_units, insc_col_units)

        zigzag_pad = 0.52 if (zigzag and count > 1) else 0.0
        col_denom = base_col_denom + zigzag_pad
        row_denom = base_row_denom

        cell = min(available_width / col_denom, available_height / row_denom)
        if font_size is not None:
            if not fit and font_size > min(available_width / base_col_denom, available_height / base_row_denom) + 1e-6:
                raise ValueError("文字超出畫布，請開啟自動適應、縮小字號或加大畫布 / Text exceeds the canvas; enable fit, reduce font size or enlarge the canvas")
            cell = min(font_size, cell) if fit else font_size
        if cell < (8 if font_size is not None else 16):
            raise ValueError("Text is too dense for this page; use a larger page or fewer characters")

        s = cell * scale_ratio
        main_h = rows * cell + (rows - 1) * cell * gap
        total_h = main_h + (0.6 * cell + num_insc_rows * s * (1 + gap) if num_insc_rows > 0 else 0.0)
        left = (width - cell * (columns + (columns - 1) * gap)) / 2
        top = (height - total_h) / 2

        slack_along = max(0.0, available_width - cell * (columns + (columns - 1) * gap))
        amp_along = min(cell * 0.35, slack_along * 0.52) if (zigzag and count > 1) else 0.0

        if zigzag and len(wrapped) > 1:
            raw_offsets = [_pseudo_rand(idx + 1) for idx in range(len(wrapped))]
            mean_offset = sum(raw_offsets) / len(raw_offsets)
            centered = [r - mean_offset for r in raw_offsets]
            max_abs = max(abs(x) for x in centered) or 1.0
            norm_line_offsets = [x / max_abs for x in centered]
        else:
            norm_line_offsets = [0.0] * max(1, len(wrapped))

        placements = []
        for line_index, line in enumerate(wrapped):
            for index, character in enumerate(line):
                col = index
                row = line_index
                x = left + col * cell * (1 + gap)
                y = top + row * cell * (1 + gap)
                if amp_along > 0.0:
                    line_stagger = norm_line_offsets[line_index] * amp_along
                    char_jitter = _pseudo_rand(line_index + 1, index + 1) * (cell * 0.09)
                    shift_along = line_stagger + char_jitter
                    shift_across = _pseudo_rand(line_index + 101, index + 1) * min(cell * 0.05, cell * gap * 0.32)
                    x = max(margin, min(width - margin - cell, x + shift_along))
                    y = max(margin, min(height - margin - cell, y + shift_across))
                placements.append(
                    {
                        "character": character,
                        "line": line_index,
                        "column": col,
                        "row": row,
                        "x": x,
                        "y": y,
                        "size": cell,
                        "is_inscription": False,
                    }
                )

        if has_insc:
            main_right = left + cell * (columns + (columns - 1) * gap)
            for row_idx, line in enumerate(clean_insc_lines):
                line_w = len(line) * s * (1 + gap) - s * gap
                row_x_start = main_right - line_w
                row_y = top + main_h + cell * 0.5 + row_idx * s * (1 + gap)
                for char_idx, character in enumerate(line):
                    placements.append(
                        {
                            "character": character,
                            "line": len(wrapped) + row_idx,
                            "column": char_idx,
                            "row": rows + row_idx,
                            "x": row_x_start + char_idx * s * (1 + gap),
                            "y": row_y,
                            "size": s,
                            "is_inscription": True,
                        }
                    )

    return {
        "width": width,
        "height": height,
        "direction": direction,
        "charactersPerLine": per_line,
        "columns": columns,
        "rows": rows,
        "zigzag": zigzag,
        "placements": placements,
    }

