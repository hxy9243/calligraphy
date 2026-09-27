"""Reusable SVG rendering and animation engine for Chinese calligraphy."""

import io
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import cairosvg
import numpy as np
from PIL import Image

# Comprehensive style configurations across historical masters:
# 1. Standard: Classical regular script (balanced Kai)
# 2. Yan: Yan Zhenqing (颜体) - muscular, heavy, powerful, expansive
# 3. Liu: Liu Gongquan (柳体) - bony, lean, crisp, structural square turns
# 4. Su: Su Shi (苏体/东坡体) - plump, horizontal emphasis, tilted/oblique stance
# 5. Wang: Wang Xizhi (王体) - fluid, dynamic, dancing running-kai rhythm
# 6. Slender: Slender Gold (瘦金体 - Zhao Ji) - delicate, razor-thin wire bones
STYLE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "slender": {
        "expansion": -8.0,
        "trace_width": 45.0,
        "thin_mode": True,
        "scale": (0.74, 0.74),
        "rotation": 0.0,
        "title": "SLENDER KAI (瘦金)",
        "school": "Song Dynasty Wire-Thin Script",
    },
    "liu": {
        "expansion": -5.0,
        "trace_width": 105.0,
        "thin_mode": True,
        "scale": (0.72, 0.76),
        "rotation": 0.0,
        "title": "LIU GONGQUAN (柳体)",
        "school": "Tang Dynasty Lean & Bony Kai",
    },
    "standard": {
        "expansion": 0.0,
        "trace_width": 165.0,
        "thin_mode": False,
        "scale": (0.74, 0.74),
        "rotation": 0.0,
        "title": "STANDARD KAI (标准楷)",
        "school": "Classical Regular Script",
    },
    "wang": {
        "expansion": -2.0,
        "trace_width": 135.0,
        "thin_mode": True,
        "scale": (0.75, 0.73),
        "rotation": -2.5,
        "title": "WANG XIZHI (王体)",
        "school": "Jin Dynasty Dynamic Running-Kai",
    },
    "su": {
        "expansion": 10.0,
        "trace_width": 175.0,
        "thin_mode": False,
        "scale": (0.79, 0.70),
        "rotation": -4.0,
        "title": "SU SHI (苏体)",
        "school": "Song Dynasty Plump Tilted Xing-Kai",
    },
    "yan": {
        "expansion": 16.48,
        "trace_width": 181.48,
        "thin_mode": False,
        "scale": (0.76, 0.76),
        "rotation": 0.0,
        "title": "YAN KAI (颜体)",
        "school": "Tang Dynasty Monumental Muscular Kai",
    },
}

STYLE_PRESETS: Dict[str, float] = {k: v["expansion"] for k, v in STYLE_CONFIGS.items()}


def get_style_config(style: Optional[str] = None, expansion: Optional[float] = None) -> Dict[str, Any]:
    """Retrieve full style parameters, allowing explicit expansion overrides."""
    key = (style or "standard").strip().lower()
    if key in STYLE_CONFIGS:
        cfg = dict(STYLE_CONFIGS[key])
    else:
        cfg = dict(STYLE_CONFIGS["standard"])
        cfg["title"] = key.upper()

    if expansion is not None:
        cfg["expansion"] = float(expansion)
        cfg["trace_width"] = max(35.0, 165.0 + cfg["expansion"])
        cfg["thin_mode"] = cfg["expansion"] < 0
    return cfg


def resolve_style_expansion(style: Optional[str] = None, expansion: Optional[float] = None) -> float:
    """Resolve numerical stroke expansion from a style name or explicit value."""
    if expansion is not None:
        return float(expansion)
    if style is None:
        return 0.0
    style_key = style.strip().lower()
    if style_key not in STYLE_CONFIGS:
        raise ValueError(
            f"Unknown style '{style}'. Choose from: {list(STYLE_CONFIGS.keys())} or pass an explicit expansion."
        )
    return STYLE_CONFIGS[style_key]["expansion"]


def trace_polyline(points: Sequence[Sequence[float]], fraction: float) -> Tuple[str, List[float]]:
    """Trace a polyline up to fractional arc length fraction in [0, 1].

    Returns (svg_path_d_string, [tip_x, tip_y]).
    """
    fraction = max(0.0, min(1.0, float(fraction)))
    pts = np.asarray(points, dtype=float)
    if len(pts) == 0:
        return "", [0.0, 0.0]
    if len(pts) == 1 or fraction <= 0:
        return f"M {pts[0, 0]:.2f} {pts[0, 1]:.2f}", pts[0].tolist()

    diffs = np.diff(pts, axis=0)
    lengths = np.hypot(diffs[:, 0], diffs[:, 1])
    total_len = np.sum(lengths)
    target_dist = total_len * fraction

    visited = [pts[0]]
    left = target_dist
    for i, seg_len in enumerate(lengths):
        if left >= seg_len:
            visited.append(pts[i + 1])
            left -= seg_len
        else:
            prog = left / seg_len if seg_len > 0 else 0
            visited.append(pts[i] + diffs[i] * prog)
            break

    path_d = "M " + " L ".join(f"{p[0]:.2f} {p[1]:.2f}" for p in visited)
    return path_d, visited[-1].tolist()


def render_character_svg(
    char_dict: dict,
    time: float,
    timings: Optional[List[dict]] = None,
    width: int = 480,
    height: int = 480,
    style: Optional[str] = "standard",
    expansion: Optional[float] = None,
    intro_delay: float = 0.4,
    stroke_duration: float = 0.55,
    outro_delay: float = 0.6,
) -> Tuple[str, float]:
    """Render an SVG frame for a single character at a given timestamp."""
    strokes = char_dict["strokes"]
    medians = char_dict["medians"]
    n_strokes = len(strokes)
    cfg = get_style_config(style, expansion)
    exp = cfg["expansion"]
    stroke_w = cfg["trace_width"]
    thin_mode = cfg["thin_mode"]
    sx, sy = cfg["scale"]
    rot = cfg["rotation"]

    if timings is None:
        timings = [
            {"start": intro_delay + i * (stroke_duration + 0.15), "duration": stroke_duration}
            for i in range(n_strokes)
        ]

    total_dur = timings[-1]["start"] + timings[-1]["duration"] + outro_delay

    defs = []
    marks = []

    for i, (outline, median) in enumerate(zip(strokes, medians)):
        mask_id = f"char_clip_{i}"
        defs.append(f'<clipPath id="{mask_id}"><path d="{outline}"/></clipPath>')

        info = timings[i]
        p = max(0.0, min(1.0, (time - info["start"]) / info["duration"]))
        if p <= 0:
            continue
        elif p >= 1:
            if thin_mode:
                d_full, _ = trace_polyline(median, 1.0)
                marks.append(
                    f'<g clip-path="url(#{mask_id})">'
                    f'<path d="{d_full}" fill="none" stroke="#22201e" stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</g>'
                )
            elif exp > 0:
                marks.append(
                    f'<path d="{outline}" fill="#22201e" stroke="#22201e" stroke-width="{exp}" stroke-linejoin="round"/>'
                )
            else:
                marks.append(f'<path d="{outline}" fill="#22201e"/>')
        else:
            d_sub, tip = trace_polyline(median, p)
            tip_r = max(8.0, 36.0 + exp * 0.2)
            marks.append(
                f'<g clip-path="url(#{mask_id})">'
                f'<path d="{d_sub}" fill="none" stroke="#22201e" stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<circle cx="{tip[0]}" cy="{tip[1]}" r="{tip_r}" fill="#161514" opacity="0.2"/>'
                f'</g>'
            )

    defs_str = "".join(defs)
    marks_str = "".join(marks)
    rot_str = f"rotate({rot} 540 540) " if rot != 0 else ""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 1080 1080">
  <defs>
    <linearGradient id="paper_bg" x2=".8" y2="1"><stop stop-color="#f7f2e7"/><stop offset="1" stop-color="#ece3d1"/></linearGradient>
    {defs_str}
  </defs>
  <rect width="1080" height="1080" fill="url(#paper_bg)"/>
  <rect x="80" y="80" width="920" height="920" fill="none" stroke="#caa985" stroke-width="2" opacity=".35"/>
  <path d="M 540 80 V 1000 M 80 540 H 1000" stroke="#caa985" stroke-dasharray="10 14" stroke-width="1.5" opacity=".2"/>
  <g transform="translate(140 160) {rot_str}scale({sx} {sy})">
    <g transform="translate(0 900) scale(1 -1)">
      {marks_str}
    </g>
  </g>
</svg>"""
    return svg, total_dur


def render_scene_svg(
    characters_data: dict,
    char_list: Sequence[str],
    time: float,
    width: int = 640,
    height: int = 340,
    style: Optional[str] = "standard",
    expansion: Optional[float] = None,
    char_size: int = 240,
    margin_x: int = 40,
    gap: int = 40,
    base_time: float = 0.45,
    stroke_time: float = 0.14,
    inter_char_gap: float = 0.35,
    title: str = "CALLIGRAPHY STUDY",
) -> Tuple[str, float]:
    """Render multiple characters arranged horizontally with sequential timing."""
    cfg = get_style_config(style, expansion)
    exp = cfg["expansion"]
    stroke_w = cfg["trace_width"]
    thin_mode = cfg["thin_mode"]
    sx, sy = cfg["scale"]
    rot = cfg["rotation"]

    schedule = []
    cursor = 0.4
    for ch in char_list:
        if ch not in characters_data:
            raise KeyError(f"Character '{ch}' not found in provided characters data.")
        data = characters_data[ch]
        dur = base_time + stroke_time * len(data["strokes"])
        schedule.append({"char": ch, "data": data, "start": cursor, "duration": dur})
        cursor += dur + inter_char_gap
    total_dur = cursor + 0.6

    defs = []
    char_elements = []

    for idx, item in enumerate(schedule):
        c_x = margin_x + idx * (char_size + gap)
        c_y = 50
        data = item["data"]
        start = item["start"]
        dur = item["duration"]
        num_strokes = len(data["strokes"])
        st_duration = dur / num_strokes

        marks = []
        for s_idx, (outline, median) in enumerate(zip(data["strokes"], data["medians"])):
            mask_id = f"scene_mask_{idx}_{s_idx}"
            defs.append(
                f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280"><path d="{outline}" fill="white" stroke="white" stroke-width="{exp if exp > 0 else 0}" stroke-linejoin="round"/></mask>'
            )

            p = max(0.0, min(1.0, (time - start - s_idx * st_duration) / st_duration))
            if p <= 0:
                continue
            elif p >= 1:
                if thin_mode:
                    d_full, _ = trace_polyline(median, 1.0)
                    marks.append(
                        f'<g mask="url(#{mask_id})">'
                        f'<path d="{d_full}" fill="none" stroke="#221f1d" stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round"/>'
                        f'</g>'
                    )
                elif exp > 0:
                    marks.append(
                        f'<path d="{outline}" fill="#221f1d" stroke="#221f1d" stroke-width="{exp}" stroke-linejoin="round"/>'
                    )
                else:
                    marks.append(f'<path d="{outline}" fill="#221f1d"/>')
            else:
                d_sub, tip = trace_polyline(median, p)
                tip_r = max(8.0, 34.0 + exp * 0.2)
                marks.append(
                    f'<g mask="url(#{mask_id})"><path d="{d_sub}" fill="none" stroke="#221f1d" stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round"/></g>'
                )
                marks.append(f'<circle cx="{tip[0]}" cy="{tip[1]}" r="{tip_r}" fill="#1a1715" opacity="0.18"/>')

        rot_str = f"rotate({rot} 512 512) " if rot != 0 else ""
        scale_val_x = (char_size / 1024.0) * (sx / 0.74)
        scale_val_y = (char_size / 1024.0) * (sy / 0.74)
        char_elements.append(
            f'<g transform="translate({c_x} {c_y}) {rot_str}scale({scale_val_x} {scale_val_y})"><g transform="translate(0 900) scale(1 -1)">{"".join(marks)}</g></g>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="scene_paper" x2=".8" y2="1"><stop stop-color="#f7f2e7"/><stop offset="1" stop-color="#ede5d6"/></linearGradient>
    {"".join(defs)}
  </defs>
  <rect width="{width}" height="{height}" fill="url(#scene_paper)"/>
  <rect x="20" y="20" width="{width - 40}" height="{height - 40}" fill="none" stroke="#d3c5af" stroke-width="1.5"/>
  <text x="30" y="42" font-family="Georgia,serif" font-size="14" letter-spacing="2" fill="#7a6c58">{title}</text>
  {"".join(char_elements)}
</svg>"""
    return svg, total_dur


def render_style_comparison_svg(
    char_dict: dict,
    time: float,
    styles: Sequence[str] = ("slender", "liu", "standard", "wang", "su", "yan"),
    titles: Optional[Sequence[str]] = None,
    width: Optional[int] = None,
    height: int = 310,
    char_size: int = 175,
    intro_delay: float = 0.4,
    stroke_duration: float = 0.55,
    outro_delay: float = 0.6,
) -> Tuple[str, float]:
    """Render a synchronized multi-style comparative SVG frame at time t."""
    strokes = char_dict["strokes"]
    medians = char_dict["medians"]
    n_strokes = len(strokes)
    timings = [
        {"start": intro_delay + i * (stroke_duration + 0.15), "duration": stroke_duration}
        for i in range(n_strokes)
    ]
    total_dur = timings[-1]["start"] + stroke_duration + outro_delay

    if width is None:
        width = max(720, len(styles) * 190)

    if titles is None:
        titles = [get_style_config(st)["title"] for st in styles]

    col_w = width / len(styles)
    defs = []
    col_groups = []

    for k, (st, ttl) in enumerate(zip(styles, titles)):
        cfg = get_style_config(st)
        exp = cfg["expansion"]
        stroke_w = cfg["trace_width"]
        thin_mode = cfg["thin_mode"]
        sx, sy = cfg["scale"]
        rot = cfg["rotation"]

        c_x = k * col_w + (col_w - char_size) / 2
        c_y = 55

        marks = []
        for i, (outline, median) in enumerate(zip(strokes, medians)):
            mask_id = f"cmp_mask_{k}_{i}"
            defs.append(
                f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280">'
                f'<path d="{outline}" fill="white" stroke="white" stroke-width="{exp if exp > 0 else 0}" stroke-linejoin="round"/></mask>'
            )

            info = timings[i]
            p = max(0.0, min(1.0, (time - info["start"]) / info["duration"]))
            if p <= 0:
                continue
            elif p >= 1:
                if thin_mode:
                    d_full, _ = trace_polyline(median, 1.0)
                    marks.append(
                        f'<g mask="url(#{mask_id})">'
                        f'<path d="{d_full}" fill="none" stroke="#22201e" stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round"/>'
                        f'</g>'
                    )
                elif exp > 0:
                    marks.append(
                        f'<path d="{outline}" fill="#22201e" stroke="#22201e" stroke-width="{exp}" stroke-linejoin="round"/>'
                    )
                else:
                    marks.append(f'<path d="{outline}" fill="#22201e"/>')
            else:
                d_sub, tip = trace_polyline(median, p)
                tip_r = max(8.0, 36.0 + exp * 0.2)
                marks.append(
                    f'<g mask="url(#{mask_id})">'
                    f'<path d="{d_sub}" fill="none" stroke="#22201e" stroke-width="{stroke_w}" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'<circle cx="{tip[0]}" cy="{tip[1]}" r="{tip_r}" fill="#161514" opacity="0.2"/>'
                    f'</g>'
                )

        scale_val_x = (char_size / 1024.0) * (sx / 0.74)
        scale_val_y = (char_size / 1024.0) * (sy / 0.74)
        header_x = k * col_w + col_w / 2
        box_x = k * col_w + 6
        box_w = col_w - 12
        rot_str = f"rotate({rot} 512 512) " if rot != 0 else ""

        col_groups.append(f"""
          <rect x="{box_x}" y="14" width="{box_w}" height="{height - 28}" fill="none" stroke="#d5c7b0" stroke-width="1.2" rx="4"/>
          <text x="{header_x}" y="36" text-anchor="middle" font-family="Georgia,serif" font-size="10.5" letter-spacing="0.5" fill="#6d5f4c">{ttl}</text>
          <g transform="translate({c_x} {c_y}) {rot_str}scale({scale_val_x} {scale_val_y})">
            <g transform="translate(0 900) scale(1 -1)">
              {''.join(marks)}
            </g>
          </g>
        """)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="cmp_bg" x2=".8" y2="1"><stop stop-color="#f7f2e7"/><stop offset="1" stop-color="#ede4d4"/></linearGradient>
    {''.join(defs)}
  </defs>
  <rect width="{width}" height="{height}" fill="url(#cmp_bg)"/>
  {''.join(col_groups)}
</svg>"""
    return svg, total_dur


def create_animation_gif(
    render_fn: Callable[[float], Tuple[str, float]],
    duration: Optional[float] = None,
    fps: int = 12,
    output_path: Optional[Union[str, Path]] = None,
    speed: float = 1.0,
) -> bytes:
    """Sample an SVG animation function over time and encode as an animated GIF."""
    if duration is None:
        _, duration = render_fn(0.0)

    n_frames = max(1, int(duration * fps / speed))
    frames = []

    for idx in range(n_frames):
        time_curr = (idx / fps) * speed
        svg_str, _ = render_fn(time_curr)
        png_data = cairosvg.svg2png(bytestring=svg_str.encode())
        frames.append(Image.open(io.BytesIO(png_data)))

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / fps),
        loop=0,
    )
    gif_bytes = buf.getvalue()

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_bytes(gif_bytes)

    return gif_bytes


def render_timeline_images(
    render_fn: Callable[[float], Tuple[str, float]],
    time_points: Sequence[float],
) -> List[Image.Image]:
    """Render PIL Images at specific time points for plotting."""
    images = []
    for t in time_points:
        svg_str, _ = render_fn(t)
        png_data = cairosvg.svg2png(bytestring=svg_str.encode())
        images.append(Image.open(io.BytesIO(png_data)))
    return images


__all__ = [
    "STYLE_CONFIGS",
    "STYLE_PRESETS",
    "create_animation_gif",
    "get_style_config",
    "render_character_svg",
    "render_scene_svg",
    "render_style_comparison_svg",
    "render_timeline_images",
    "resolve_style_expansion",
    "trace_polyline",
]
