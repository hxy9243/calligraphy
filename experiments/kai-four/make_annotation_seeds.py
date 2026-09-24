"""Create editable, automatically proposed per-stroke labels for the browser UI."""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import mask_warp as previous
import render as base

HERE = Path(__file__).resolve().parent
SIZE = 300


def runs(mask):
    flat = mask.ravel().astype(np.uint8)
    edges = np.flatnonzero(np.diff(np.r_[0, flat, 0]))
    return [[int(a), int(b - a)] for a, b in zip(edges[::2], edges[1::2])]


def create():
    source = np.asarray(Image.open(base.SOURCE).convert("L"))
    reference = np.asarray(Image.open(base.TEMPLATE).convert("L")) < 100
    ry, rx = np.where(reference)
    reference_box = (rx.min(), ry.min(), rx.max(), ry.max())
    data = json.loads(base.DATA.read_text())
    output = {"version": 1, "character": "書", "size": SIZE, "styles": []}
    for name, (x0, y0, x1, y1, bright, threshold) in zip(base.NAMES, base.ROIS):
        ink = base.ink_mask(source[y0:y1, x0:x1], bright, threshold)
        yy, xx = np.where(ink)
        target_box = (xx.min(), yy.min(), xx.max(), yy.max())
        paths = base.fit_medians(data["medians"], reference_box, target_box)
        score = []
        for i in range(len(paths)):
            alpha = np.asarray(Image.open(previous.MASKS / f"{i:02d}.png").convert("RGBA"))[:, :, 3] / 255
            mask = previous.warp_stroke(alpha, ink.shape, reference_box, target_box)
            mask, _ = previous.translate_to_ink(mask, ink)
            score.append(ndi.distance_transform_edt(~mask) - .4 * ndi.distance_transform_edt(mask))
        owner = np.argmin(np.stack(score), axis=0)
        strokes = []
        for i, path in enumerate(paths):
            mask = np.asarray(Image.fromarray(np.uint8(ink & (owner == i)) * 255).resize((SIZE, SIZE), Image.Resampling.NEAREST)) > 0
            points = [[round(float(x * SIZE / ink.shape[1]), 1), round(float(y * SIZE / ink.shape[0]), 1)] for x, y in path]
            strokes.append({"maskRLE": runs(mask), "median": points})
        output["styles"].append({"name": name, "roi": [x0, y0, x1, y1], "bright": bright,
                                 "threshold": threshold, "strokes": strokes})
    (HERE / "annotation-seeds.json").write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Wrote {HERE / 'annotation-seeds.json'}")


if __name__ == "__main__":
    create()
