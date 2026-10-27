"""Shared geometry for glyph lanes, paper rules and stamp placement."""


def ruled_page_grid(width, height, direction, lane_count):
    """Divide the inner paper frame into equal writing lanes."""
    short_side = min(width, height)
    margin = max(10, int(round(short_side * 0.048)))
    inset = max(3, int(round(short_side * 0.0065)))
    inner = [margin + inset, margin + inset,
             width - 1 - margin - inset, height - 1 - margin - inset]
    start, end = (inner[0], inner[2]) if direction == "vertical-rl" else (inner[1], inner[3])
    pitch = (end - start) / lane_count
    return {
        "outer_box": [max(2, inner[0] - inset), max(2, inner[1] - inset),
                      min(width - 3, inner[2] + inset), min(height - 3, inner[3] + inset)],
        "inner_box": inner,
        "dividers": tuple(round(start + k * pitch, 2) for k in range(1, lane_count)),
        "lane_centers": tuple(round(start + (k + .5) * pitch, 2) for k in range(lane_count)),
        "lane_width": round(pitch, 2),
        "n_lanes": lane_count,
    }
