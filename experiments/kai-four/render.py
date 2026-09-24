"""Reconstruct four plausible writing animations from one historical comparison scan.

The image supplies the *final ink*. Hanzi Writer's 書 medians supply an order
prior. Nearest-path projection assigns each ink pixel to one stroke and a
position along that stroke. These are inferred paths, not recorded movements.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source.jpg"
DATA = HERE / "shu.json"
TEMPLATE = HERE / "template.png"
OUTPUT = HERE / "four-kai-shu.mp4"
FPS = 24
WIDTH, HEIGHT = 1200, 1320
DURATION = 12
ROIS = [
    # x0, y0, x1, y1, bright ink?, threshold. Crop away neighboring marks.
    (5, 3, 280, 296, True, 135),
    (316, 4, 584, 297, True, 140),
    (52, 306, 282, 591, True, 130),
    (312, 305, 590, 596, False, 125),
]
NAMES = ["OUYANG XUN", "YAN ZHENQING", "LIU GONGQUAN", "ZHAO MENGFU"]
POSITIONS = [(80, 206), (670, 206), (80, 733), (670, 733)]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def ink_mask(image: np.ndarray, bright: bool, threshold: int) -> np.ndarray:
    binary = image > threshold if bright else image < threshold
    labels, _ = ndi.label(binary)
    sizes = np.bincount(labels.ravel())
    return binary & (sizes[labels] > 35)


def fit_medians(medians: list, reference_box: tuple, target_box: tuple) -> list:
    rx0, ry0, rx1, ry1 = reference_box
    tx0, ty0, tx1, ty1 = target_box
    sx, sy = (tx1 - tx0) / (rx1 - rx0), (ty1 - ty0) / (ry1 - ry0)
    return [
        np.array(
            [[tx0 + (x * 300 / 1024 - rx0) * sx,
              ty0 + ((900 - y) * 300 / 1024 - ry0) * sy] for x, y in stroke],
            dtype=np.float32,
        )
        for stroke in medians
    ]


def infer_exposure(mask: np.ndarray, paths: list) -> tuple[np.ndarray, dict]:
    y, x = np.where(mask)
    pixels = np.stack((x, y), axis=1).astype(np.float32)
    best = np.full(len(pixels), np.inf, dtype=np.float32)
    runner_up = best.copy()
    owners = np.full(len(pixels), -1, dtype=np.int16)
    progress = np.zeros(len(pixels), dtype=np.float32)

    for stroke, points in enumerate(paths):
        segments = np.diff(points, axis=0)
        lengths = np.linalg.norm(segments, axis=1)
        total = lengths.sum()
        prefix = np.r_[0, np.cumsum(lengths)]
        nearest = np.full(len(pixels), np.inf, dtype=np.float32)
        nearest_progress = np.zeros(len(pixels), dtype=np.float32)
        for j, (origin, vector) in enumerate(zip(points[:-1], segments)):
            length2 = max(float(np.dot(vector, vector)), 1e-6)
            u = np.clip(((pixels - origin) @ vector) / length2, 0, 1)
            distance2 = np.sum((pixels - (origin + u[:, None] * vector)) ** 2, axis=1)
            changed = distance2 < nearest
            nearest[changed] = distance2[changed]
            nearest_progress[changed] = (prefix[j] + u[changed] * lengths[j]) / total
        changed = nearest < best
        runner_up[changed] = best[changed]
        runner_up[~changed] = np.minimum(runner_up[~changed], nearest[~changed])
        best[changed] = nearest[changed]
        owners[changed] = stroke
        progress[changed] = nearest_progress[changed]

    distance = np.sqrt(best)
    assigned_exposure = 1.15 + owners * 0.83 + progress * 0.70
    exposure = np.full(mask.shape, np.inf, dtype=np.float32)
    exposure[y, x] = assigned_exposure
    # Let already-revealed ink claim a few pixels across ambiguous crossing
    # seams. A narrow spatial propagation is less invasive than assigning an
    # entire neighboring stroke to the earlier median.
    exposure = ndi.minimum_filter(exposure, size=13)
    exposure[~mask] = np.inf
    diagnostics = {
        "ink_pixels": len(pixels),
        "median_distance_p50_px": round(float(np.median(distance)), 1),
        "median_distance_p90_px": round(float(np.percentile(distance, 90)), 1),
        "fraction_over_20px": round(float(np.mean(distance > 20)), 3),
        "ambiguous_fraction": round(float(np.mean(np.sqrt(runner_up) - distance < 3)), 3),
    }
    return exposure, diagnostics


def setup():
    scan = np.asarray(Image.open(SOURCE).convert("L"))
    data = json.loads(DATA.read_text())
    reference = np.asarray(Image.open(TEMPLATE).convert("L")) < 100
    ry, rx = np.where(reference)
    reference_box = rx.min(), ry.min(), rx.max(), ry.max()
    styles, report = [], {}

    for name, (x0, y0, x1, y1, bright, threshold) in zip(NAMES, ROIS):
        crop = scan[y0:y1, x0:x1]
        mask = ink_mask(crop, bright, threshold)
        yy, xx = np.where(mask)
        target_box = xx.min(), yy.min(), xx.max(), yy.max()
        paths = fit_medians(data["medians"], reference_box, target_box)
        exposure, diagnostics = infer_exposure(mask, paths)
        report[name] = diagnostics

        # Preserve the reference's varied ink tone, on a common paper surface.
        strength = (crop - threshold) / (245 - threshold) if bright else (threshold - crop) / max(threshold - 45, 1)
        alpha = np.uint8(np.clip((0.64 + 0.36 * strength) * 255, 0, 255)) * mask
        ink = np.empty((*mask.shape, 4), dtype=np.uint8)
        ink[:, :, :3] = [48, 43, 38] if bright else [78, 61, 48]
        ink[:, :, 3] = alpha
        styles.append((ink, exposure))
    return styles, report


def background() -> Image.Image:
    rng = np.random.default_rng(7)
    texture = rng.normal(0, 1.6, (HEIGHT, WIDTH, 1))
    paper = np.array([247, 242, 231], dtype=np.float32) + texture
    paper += np.linspace(3, -3, HEIGHT)[:, None, None]
    image = Image.fromarray(np.uint8(np.clip(paper, 0, 255)), "RGB")
    draw = ImageDraw.Draw(image)
    heading = ImageFont.truetype(FONT, 31)
    label = ImageFont.truetype(FONT, 23)
    small = ImageFont.truetype(FONT, 18)
    draw.text((78, 63), "FOUR HANDS / ONE CHARACTER", font=heading, fill="#413b34")
    draw.text((80, 117), "Regular-script writing study · reconstructed from a static image", font=small, fill="#786d5e")
    draw.line((78, 158, 1122, 158), fill="#c9bdab", width=2)
    for name, (x, y) in zip(NAMES, POSITIONS):
        draw.text((x, y), name, font=label, fill="#514940")
        draw.line((x, y + 40, x + 450, y + 40), fill="#d3c7b5", width=1)
    draw.line((78, 1248, 1122, 1248), fill="#c9bdab", width=2)
    draw.text((80, 1271), "ORIGINAL INK  ·  INFERRED STROKE ORDER  ·  NOT RECORDED MOTION", font=small, fill="#786d5e")
    return image


def render(output: Path = OUTPUT):
    styles, diagnostics = setup()
    (HERE / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    base = background()
    draw_font = ImageFont.truetype(FONT, 18)
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "pipe:0", "-an", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(output)],
        stdin=subprocess.PIPE,
    )
    try:
        for frame in range(DURATION * FPS):
            t = frame / FPS
            canvas = base.copy()
            for (ink, exposure), (x, y) in zip(styles, POSITIONS):
                rgba = ink.copy()
                rgba[:, :, 3] *= t >= exposure
                tile = Image.fromarray(rgba, "RGBA").resize((420, 420), Image.Resampling.BICUBIC)
                canvas.paste(tile, (x + 12, y + 68), tile)
            draw = ImageDraw.Draw(canvas)
            number = min(10, max(0, int((t - 1.15) / 0.83) + 1))
            draw.text((1010, 117), f"{number:02d} / 10", font=draw_font, fill="#8b4b3e")
            ffmpeg.stdin.write(canvas.tobytes())
            if frame % FPS == 0:
                print(f"\rRendering {frame // FPS} / {DURATION} seconds", end="", flush=True)
    finally:
        ffmpeg.stdin.close()
        code = ffmpeg.wait()
        if code:
            raise RuntimeError(f"FFmpeg exited {code}")
    print(f"\nWrote {output}")
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    render()
