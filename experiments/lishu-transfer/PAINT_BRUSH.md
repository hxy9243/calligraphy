# Pressure-controlled paint brush experiment

This opt-in experiment starts from the six committed smooth-outline glyphs
(清、泉、石 on reference and light sheets), on top of commit `34a254a`.
It reconstructs each stroke as a moving brush, rather than revealing the SVG
through the previous progress field. Existing experiments are unchanged.

## Brush rules

1. Extract the longest medial route from each isolated outline, pruning short
   skeleton branches. Use the existing character median direction to orient it.
2. If lateral deviation is small relative to stroke width, replace the route
   with an exact straight line. Otherwise simplify and interpolate a smooth
   path, retaining large turns and the lishu wave. No global horizontal snap:
   a naturally sloping shaft retains its slope.
3. Measure contiguous cross-sections for width. Cap width by local interior
   distance to prevent a corner cross-section from swallowing an entire arm.
   Smooth the pressure with sparse shape-preserving interpolation.
4. Press at a fixed starting point before travelling. Use overlapping elliptical
   footprints, a broader head, smooth width changes, and a tapered lift when
   the source ending is thin. Blunt endings stay blunt.
5. Slow down at the initial press, heavy sections and turns. Sample footprints
   at roughly 0.65-pixel spacing on a 480-pixel canvas, render at 3x resolution,
   then downsample. Footprints accumulate persistently; there is no final
   whole-character replacement and no clipping to the old outline.
6. Compose complete strokes with maximum opacity, preserving shared crossings.

These are geometric brush heuristics, not a bristle/fluid simulation or verified
historical ductus. The initial path orientation uses an overall direction prior;
complex hooks can need explicit path controls. The six exported JSON files are
editable brush trajectories, pressure samples, and timing; fitting currently
regenerates them on each run. `BrushPainter` accepts those same stroke records
directly, independently of the fitter or SVG outlines.

## Results

| Sheet | Character | Silhouette IoU against previous outline |
| --- | --- | --- |
| Reference | 清 | 0.881 |
| Reference | 泉 | 0.839 |
| Reference | 石 | 0.888 |
| Light | 清 | 0.808 |
| Light | 泉 | 0.805 |
| Light | 石 | 0.827 |

These compare with the **previous SVG outline**, not the original artwork.
The model yields smooth continuous shafts and brush-tip-led motion, at the cost
of some original shape and terminal detail. Thin strokes, corners and inherited
ownership errors remain the weakest cases. Pressure is inferred from geometry,
not measured from real handwriting. Solid ink is deliberate for evaluating
motion; dry-brush texture is not synthesized here.

## Reproduce

```bash
python -m pip install -r experiments/lishu-transfer/requirements-brush.txt
python experiments/lishu-transfer/paint_brush.py --video
python -m unittest discover -s experiments/lishu-transfer -p test_paint_brush.py -v
```

The script only needs the already committed `outlines/*.svg` and
`experiments/stroke-ownership/ownership-characters.json`; no old work caches,
generated source PNG downloads, Node modules, or image-generation service.

Outputs:

- `Lishu-Paint-Brush.mp4`: previous outline as a static reference, live brush
  painting, and the isolated active stroke with its centerline and moving tip.
- `Lishu-Brush-Comparison.png`: all six completed reconstructions and paths.
- `brush/*.json`: reproducible stroke parameters and comparison metrics.

The four brush tests cover straight geometry, preserved turns and connected
paint, monotonic/frame-rate-independent accumulation, and invalid inputs.
All 17 tests across the lishu and stroke-ownership directories pass, including
these four new brush tests. The comparison/video are review artifacts, not proof
of calligraphic fidelity.

Next useful improvement: explicit corner and terminal controls, then optimize
path and pressure jointly against silhouette with smoothness penalties. This
should recover more of the thin strokes without returning to a raster reveal.
