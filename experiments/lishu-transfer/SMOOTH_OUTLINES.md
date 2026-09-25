# Explicit smooth outlines: geometry-first experiment

This is a separate experiment, not a replacement for the exact-reconstruction
pipeline. Tested on 清、泉、石 from both existing sheets (six glyphs).
Main was rechecked at `4e2a972`; the starting experiment commit is `2fa834c`.

## Approach

1. Initialize from the previous refined stroke layers, including its four
   sample-specific controls. Threshold at 0.35 and retain each stroke's largest
   external component. This deliberately removes detached fragments and holes.
2. Resample its boundary at uniform arc length, smooth boundary coordinates,
   and fit a periodic cubic spline with knots approximately 12 pixels apart.
   Export the equivalent closed cubic Bézier path for every stroke as SVG.
3. Try boundary smoothing scales of 2, 4, and 7 pixels on the 480-pixel canvas.
   Choose the smoothest candidate whose combined silhouette IoU is at least
   0.94. If none qualifies, select the highest-IoU candidate and flag the miss.
   This shared-union candidate selection is NOT joint control-point optimization.
4. Fill and antialias the outlines directly. No clipping against source pixels,
   coverage normalization, or final whole-character replacement is applied.
   Overlaps remain present in both strokes; max compositing avoids dark seams.
5. Extend the existing progress field by nearest interior point for animation.
   This tests geometry, not a new model of brush motion or historical ductus.

## Results and limitations

All six candidates satisfy the silhouette floor: IoU 0.9425–0.9645. Missing
target foreground is 2.49–3.87%; added foreground is 1.09–2.55%, each relative
to target foreground area. These metrics threshold at 0.5; they do not mean
pixel-exact reconstruction. Full opacity errors and candidate results are in
`outline-metrics.json`.

Visually, short stems and falling strokes have cleaner boundaries. However,
solid ink looks more typographic; dry brush, fine tips, and some angular detail
are lost. Larger ownership defects can survive contour smoothing. This is an
automatic outline fit initialized by the previous partly annotated decomposition,
not a general solution to stroke separation. Cubic continuity does not guarantee
good calligraphic shape or absence of self-intersections for arbitrary inputs.

Next: author corner/end constraints and optimize asymmetric sides at difficult
junctions, then add interior ink texture without using it to cut the outline.
Keep the original exact-reconstruction option for comparisons.

## Inspect and reproduce

- `Outline-Comparison.png`: target, new union, outline overlay, selected old/new stroke.
- `Outline-All-Strokes.png`: every stroke, previous above/new below.
- `Lishu-Smooth-Outlines.mp4`: side-by-side writing and isolated active stroke.
- `outlines/*.svg`: individually editable Bézier paths, named by stroke number.

Generate prior caches with `smooth_strokes.py` followed by `refine_strokes.py`,
then run `python3 experiments/lishu-transfer/outline_strokes.py --video` from
the repository root. Existing Python requirements are unchanged.

Validation: 13 unit tests across both experiment directories; runtime checks
for all six glyphs verify finite bounded opacity, blank starts, monotonic reveal,
nonzero contribution by every stroke, and a final frame equal to the stroke
union. No assertion of equality to the original target is made for this mode.
