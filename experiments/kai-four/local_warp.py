"""Register continuous brush paths locally and reveal connected contact regions.

The video is a geometric hypothesis from a final scan, not recovered brush motion.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

import mask_warp as previous
import render as baseline

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "four-kai-local-warp.mp4"


def sample(field, coords):
    return ndi.map_coordinates(field, [coords[:, 1], coords[:, 0]], order=1, mode="nearest")


def deform_path(points, ink, limit=17):
    """Find a smoothly varying normal displacement toward the scan's ink.

    Dynamic programming penalizes displacement and abrupt changes so a centerline
    cannot hop independently between crossed strokes at adjacent samples.
    """
    path = previous.smooth_path(points)[::3].astype(np.float32)
    delta = np.gradient(path, axis=0)
    normal = np.column_stack([-delta[:, 1], delta[:, 0]])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-6)
    offsets = np.arange(-limit, limit + 1, 2, dtype=np.float32)
    candidate = path[:, None, :] + normal[:, None, :] * offsets[None, :, None]
    distance = ndi.distance_transform_edt(~ink).astype(np.float32)
    flat = candidate.reshape(-1, 2)
    proximity = sample(distance, flat).reshape(len(path), len(offsets))
    cost = np.minimum(proximity, 18) ** 2 + 0.055 * offsets[None, :] ** 2
    # An end point is allowed to move, but should not jump off its median.
    back = np.zeros((len(path), len(offsets)), np.int16)
    total = cost[0]
    transition = 0.75 * (offsets[:, None] - offsets[None, :]) ** 2
    for j in range(1, len(path)):
        matrix = transition + total[None, :]
        back[j] = np.argmin(matrix, axis=1)
        total = cost[j] + matrix[np.arange(len(offsets)), back[j]]
    choices = np.zeros(len(path), np.int16)
    choices[-1] = int(np.argmin(total))
    for j in range(len(path) - 1, 0, -1):
        choices[j - 1] = back[j, choices[j]]
    displacement = ndi.gaussian_filter1d(offsets[choices], 1.4)
    return path + normal * displacement[:, None], displacement


def scan_radii(path, ink, reference_mask):
    """Estimate width across the source ink; suppress inflated crossings."""
    tangent = np.gradient(path, axis=0)
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-6)
    widths = []
    template_dt = ndi.distance_transform_edt(reference_mask).astype(np.float32)
    for point, direction in zip(path, normal):
        offsets = np.arange(-36, 37, dtype=np.float32)
        samples = point[None, :] + offsets[:, None] * direction[None, :]
        hit = sample(ink.astype(np.float32), samples) > 0.5
        hits = np.flatnonzero(hit)
        center = int(hits[np.argmin(np.abs(hits - 36))]) if len(hits) else 36
        left = center
        right = center
        while left > 0 and hit[left - 1]:
            left -= 1
        while right < 72 and hit[right + 1]:
            right += 1
        # Include a small centerline-to-ink gap; the old estimate collapsed
        # broad strokes when the initial median landed just outside the ink.
        observed = max(3.0, max(abs(left - 36), abs(right - 36)) + 1.0)
        prior = max(2.5, float(sample(template_dt, point[None, :])[0]))
        widths.append(min(observed, max(9, 3.0 * prior), 32))
    radii = ndi.median_filter(np.asarray(widths, np.float32), size=7)
    return ndi.gaussian_filter1d(radii, 1.3).clip(3.0, 32)


def sweep_layers(path, radii, shape):
    """Every prefix is a single connected sequence of overlapping brush stamps."""
    steps = max(80, len(path) * 3)
    t = np.linspace(0, len(path) - 1, steps)
    x = np.interp(t, np.arange(len(path)), path[:, 0])
    y = np.interp(t, np.arange(len(path)), path[:, 1])
    widths = np.interp(t, np.arange(len(path)), radii)
    frames = []
    image = Image.new("L", (shape[1], shape[0]))
    draw = ImageDraw.Draw(image)
    for j, (cx, cy, r) in enumerate(zip(x, y, widths)):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        if j == 0 or j == steps - 1 or j % 2 == 0:
            frames.append(np.asarray(image, dtype=np.uint8).copy())
    return np.stack(frames)


def prepare():
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
        layers, displacements, coverages = [], [], []
        ink_distance = ndi.distance_transform_edt(~ink)
        for i, points in enumerate(paths):
            source = np.asarray(Image.open(previous.MASKS / f"{i:02d}.png").convert("RGBA"))[:, :, 3] / 255
            reference_mask = previous.warp_stroke(source, ink.shape, reference_box, target_box)
            path, moved = deform_path(points, ink)
            radii = scan_radii(path, ink, reference_mask)
            # The brush is allowed to bridge a tiny scan gap. Suppress stamps
            # far from observed ink, except a thin centerline to maintain motion.
            allowed = ink_distance <= 2.5
            stamp = sweep_layers(path, radii, ink.shape)
            visible = stamp * allowed[None, :, :]
            layers.append(visible)
            displacements.append(round(float(np.sqrt(np.mean(moved ** 2))), 2))
            coverages.append(round(float(np.mean((stamp[-1] > 0)[ink])), 3))
        report[name] = {"rms_normal_deformation_px": displacements,
                        "fraction_of_scan_ink_touched_by_each_stroke": coverages,
                        "union_ink_coverage": round(float(np.mean(np.any(np.stack([l[-1] > 0 for l in layers]), axis=0)[ink])), 3)}
        strength = (crop - threshold) / (245 - threshold) if bright else (threshold - crop) / max(threshold - 45, 1)
        alpha = np.uint8(np.clip((0.64 + 0.36 * strength) * 255, 0, 255)) * ink
        rgba = np.empty((*ink.shape, 4), np.uint8)
        rgba[:, :, :3] = [48, 43, 38] if bright else [78, 61, 48]
        rgba[:, :, 3] = alpha
        styles.append((rgba, layers, ink))
    return styles, report


def render(output=OUTPUT):
    styles, report = prepare()
    (HERE / "local-warp-diagnostics.json").write_text(json.dumps(report, indent=2) + "\n")
    base = baseline.background()
    font = ImageFont.truetype(baseline.FONT, 18)
    ffmpeg = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{baseline.WIDTH}x{baseline.HEIGHT}", "-r", str(baseline.FPS), "-i", "pipe:0", "-an",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", str(output)],
         stdin=subprocess.PIPE)
    try:
        for frame in range(baseline.DURATION * baseline.FPS):
            t = frame / baseline.FPS
            canvas = base.copy()
            for (source, layers, ink), (x, y) in zip(styles, baseline.POSITIONS):
                paint = np.zeros(ink.shape, dtype=np.uint8)
                for i, layer in enumerate(layers):
                    phase = np.clip((t - 1.15 - i * 0.83) / 0.70, 0, 1)
                    if t >= 1.15 + i * 0.83:
                        paint = np.maximum(paint, layer[int(phase * (len(layer) - 1))])
                rgba = source.copy()
                # Source scan supplies texture. Fill only narrow holes inside
                # brush contact to avoid disconnected flecks during the sweep.
                # Blend the unregistered residual ink in at the end; fade any
                # temporary bridges away so the held frame is the exact scan.
                completion = np.clip((t - 9.45) / 1.0, 0, 1)
                rgba[:, :, 3] = np.maximum(rgba[:, :, 3] * (paint > 0),
                    np.uint8((paint > 0) & ~ink) * np.uint8(170 * (1 - completion)))
                rgba[:, :, 3] = np.maximum(rgba[:, :, 3], np.uint8(source[:, :, 3] * completion))
                tile = Image.fromarray(rgba, "RGBA").resize((420, 420), Image.Resampling.BICUBIC)
                canvas.paste(tile, (x + 12, y + 68), tile)
            draw = ImageDraw.Draw(canvas)
            draw.text((1010, 117), f"{min(10, max(0, int((t - 1.15) / 0.83) + 1)):02d} / 10", font=font, fill="#8b4b3e")
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
