"""Warp ordered stroke silhouettes to four scanned Kai hands and animate them.

This is an experiment in source-image registration, not historical motion recovery.
The masks determine stroke identity; ink color and final contour come from the scan.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator

import render as baseline

HERE = Path(__file__).resolve().parent
MASKS = HERE / "stroke-masks"
OUTPUT = HERE / "four-kai-mask-warp.mp4"


def smooth_path(points: np.ndarray) -> np.ndarray:
    """Resample a median continuously without overshooting acute stroke turns."""
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    keep = np.r_[True, np.diff(distance) > 0.01]
    distance, points = distance[keep], points[keep]
    if len(distance) < 2:
        return points
    samples = np.linspace(0, distance[-1], max(60, int(distance[-1] * 1.5)))
    return np.column_stack([PchipInterpolator(distance, points[:, k])(samples) for k in (0, 1)])


def project_progress(pixels: np.ndarray, path: np.ndarray) -> np.ndarray:
    """Project ink onto a densely sampled, continuous stroke centerline."""
    lengths = np.linalg.norm(np.diff(path, axis=0), axis=1)
    origin = path[:-1]
    cumulative = np.r_[0, np.cumsum(lengths)]
    nearest = np.full(len(pixels), np.inf, dtype=np.float32)
    progress = np.zeros(len(pixels), dtype=np.float32)
    for j, vector in enumerate(np.diff(path, axis=0)):
        u = np.clip((pixels - origin[j]) @ vector / max(float(vector @ vector), 1e-8), 0, 1)
        d2 = np.sum((pixels - (origin[j] + u[:, None] * vector)) ** 2, axis=1)
        update = d2 < nearest
        nearest[update] = d2[update]
        progress[update] = (cumulative[j] + u[update] * lengths[j]) / cumulative[-1]
    return progress


def warp_stroke(image: np.ndarray, shape: tuple, reference_box: tuple, target_box: tuple) -> np.ndarray:
    ry0, rx0 = np.indices(shape, dtype=np.float32)
    refx0, refy0, refx1, refy1 = reference_box
    tx0, ty0, tx1, ty1 = target_box
    rx = (rx0 - tx0) * (refx1 - refx0) / (tx1 - tx0) + refx0
    ry = (ry0 - ty0) * (refy1 - refy0) / (ty1 - ty0) + refy0
    return ndi.map_coordinates(image, [ry, rx], order=1, mode="constant", cval=0) > 0.42


def translate_to_ink(template: np.ndarray, ink: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
    """Small regularized translation per stroke; no unconstrained shape fitting."""
    best, moved, offset = -np.inf, template, (0, 0)
    area = max(template.sum(), 1)
    for dy in range(-10, 11, 2):
        for dx in range(-10, 11, 2):
            shifted = ndi.shift(template, (dy, dx), order=0, mode="constant", cval=0)
            score = np.count_nonzero(shifted & ink) / area - 0.0012 * (dx * dx + dy * dy)
            if score > best:
                best, moved, offset = score, shifted, (dx, dy)
    return moved, offset


def infer_masks(ink: np.ndarray, paths: list, reference_box: tuple, target_box: tuple):
    warped, offsets = [], []
    for i in range(len(paths)):
        source = np.asarray(Image.open(MASKS / f"{i:02d}.png").convert("RGBA"))[:, :, 3] / 255
        shape = warp_stroke(source, ink.shape, reference_box, target_box)
        shape, offset = translate_to_ink(shape, ink)
        warped.append(shape)
        offsets.append(offset)

    # Score *distance to the complete warped silhouette*. At a crossing both
    # silhouettes retain their own interior. Source pixels are assigned to one
    # silhouette for final rendering, so every source-ink pixel is retained.
    scores = []
    for shape in warped:
        outside = ndi.distance_transform_edt(~shape)
        inside = ndi.distance_transform_edt(shape)
        scores.append(outside - 0.4 * inside)
    score = np.stack(scores)
    owner = np.argmin(score, axis=0)
    expose = np.full(ink.shape, np.inf, np.float32)
    segmentation = np.zeros((*ink.shape, 3), np.uint8)
    colors = np.array([[156, 76, 63], [188, 118, 68], [172, 155, 75], [87, 141, 100],
                       [74, 137, 168], [112, 107, 172], [170, 93, 144], [88, 111, 82],
                       [153, 105, 80], [93, 124, 140]], dtype=np.uint8)
    segmentation[ink] = colors[owner[ink]]
    components = []
    for i, path in enumerate(paths):
        yy, xx = np.where(ink & (owner == i))
        points = np.column_stack((xx, yy)).astype(np.float32)
        dx, dy = offsets[i]
        smooth = smooth_path(path + np.array([dx, dy]))
        if len(points):
            progress = project_progress(points, smooth)
            expose[yy, xx] = 1.15 + i * 0.83 + progress * 0.70
        # Measure sizeable separated ink islands in the assigned stroke.
        labels, n = ndi.label(ink & (owner == i))
        sizes = np.bincount(labels.ravel())[1:]
        components.append(int(np.count_nonzero(sizes >= 12)))
    return expose, segmentation, {"offsets_px": offsets, "stroke_components_over_12px": components,
        "source_ink_coverage": round(float(np.isfinite(expose[ink]).mean()), 4),
        "ink_inside_warped_mask": round(float(np.mean(score.min(axis=0)[ink] <= 0)), 3)}


def setup():
    scan = np.asarray(Image.open(baseline.SOURCE).convert("L"))
    data = json.loads(baseline.DATA.read_text())
    reference = np.asarray(Image.open(baseline.TEMPLATE).convert("L")) < 100
    ry, rx = np.where(reference)
    reference_box = (rx.min(), ry.min(), rx.max(), ry.max())
    styles, report = [], {}
    for name, (x0, y0, x1, y1, bright, threshold) in zip(baseline.NAMES, baseline.ROIS):
        crop = scan[y0:y1, x0:x1]
        ink = baseline.ink_mask(crop, bright, threshold)
        yy, xx = np.where(ink)
        target_box = (xx.min(), yy.min(), xx.max(), yy.max())
        paths = baseline.fit_medians(data["medians"], reference_box, target_box)
        exposure, labels, report[name] = infer_masks(ink, paths, reference_box, target_box)
        Image.fromarray(labels).save(HERE / f"mask-labels-{baseline.NAMES.index(name)}.png")
        strength = (crop - threshold) / (245 - threshold) if bright else (threshold - crop) / max(threshold - 45, 1)
        alpha = np.uint8(np.clip((0.64 + 0.36 * strength) * 255, 0, 255)) * ink
        rgba = np.empty((*ink.shape, 4), np.uint8)
        rgba[:, :, :3] = [48, 43, 38] if bright else [78, 61, 48]
        rgba[:, :, 3] = alpha
        styles.append((rgba, exposure))
    return styles, report


def render(output=OUTPUT):
    if not MASKS.exists():
        raise RuntimeError("Run `node experiments/kai-four/stroke_masks.mjs` first")
    styles, report = setup()
    (HERE / "mask-warp-diagnostics.json").write_text(json.dumps(report, indent=2) + "\n")
    base = baseline.background()
    ffmpeg = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
       "-pix_fmt", "rgb24", "-s", f"{baseline.WIDTH}x{baseline.HEIGHT}", "-r", str(baseline.FPS),
       "-i", "pipe:0", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
       "-movflags", "+faststart", str(output)], stdin=subprocess.PIPE)
    try:
        for frame in range(baseline.DURATION * baseline.FPS):
            t = frame / baseline.FPS
            canvas = base.copy()
            for (ink, exposure), (x, y) in zip(styles, baseline.POSITIONS):
                rgba = ink.copy()
                rgba[:, :, 3] *= t >= exposure
                tile = Image.fromarray(rgba, "RGBA").resize((420, 420), Image.Resampling.BICUBIC)
                canvas.paste(tile, (x + 12, y + 68), tile)
            draw = ImageDraw.Draw(canvas)
            draw.text((1010, 117), f"{min(10, max(0, int((t - 1.15) / 0.83) + 1)):02d} / 10",
                      font=ImageFont.truetype(baseline.FONT, 18), fill="#8b4b3e")
            ffmpeg.stdin.write(canvas.tobytes())
            if frame % baseline.FPS == 0:
                print(f"\rRendering {frame // baseline.FPS} / {baseline.DURATION} seconds", end="", flush=True)
    finally:
        ffmpeg.stdin.close()
        if ffmpeg.wait():
            raise RuntimeError("FFmpeg encode failed")
    print(f"\nWrote {output}\n{json.dumps(report, indent=2)}")


if __name__ == "__main__":
    render()
