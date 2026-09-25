# Smooth stroke surfaces and complete reconstruction

## Why this follow-up exists

The previous aspect-fit change was based on main `4e2a972`, which contains the
overlap-preserving implementation. Main was checked again and remains at that
commit; there were no newer changes to merge. The problem was not stale code:
it still clipped source ink with hard, low-resolution, warped masks. Those
masks produced squared-off boundaries, teeth from neighboring arms, and
notches at intersections.

The user requested independently smooth stroke surfaces that reconstruct the
character. This experiment changes stroke geometry and layer compositing, not
only registration or playback speed. Production main remains untouched.

## Method

1. Reuse the previous aspect-fitted registration to infer ordered stroke fields.
2. Gather points along each stroke in progress order. Fit a continuous
   centerline and measure local width normal to its tangent.
3. Smooth centerline and width separately; interpolate a 160-point ribbon with
   rounded ends. This replaces jagged support boundaries with a continuous
   stroke envelope. Very small/degenerate strokes fall back to their isolated
   support rather than inventing a path.
4. Rasterize the envelopes at 480×480 and give their edges a narrow antialias
   transition. The original 160×160 registration remains the topology prior;
   higher-resolution source crops supply the ink texture.
5. Turn envelope distance fields into overlapping alpha masks. Normalize each
   pixel by its strongest affinity, so at least one layer contains that source
   pixel at full strength. Max-compositing all stroke layers therefore exactly
   reconstructs the normalized source. Intersections can belong to multiple
   strokes without being double-darkened.
6. Reveal each stroke along its new centerline's arc length using a smoothstep
   front. Every video frame is composed from the layers; there is no final
   whole-character replacement or residual-ink fill.

Natural brush texture at the character's outer boundary is preserved. We do
not blur the final character to conceal poor segmentation. An initial
signed-distance-only smoothing attempt softened seams but left visible nubs
and notches, so it was replaced by the ribbon fit before exporting this result.

## Results and limits

The same two ten-character sheets were evaluated: **20 target glyphs**.

- Max-composite reconstruction error: **0.0** at every pixel of all 20
  normalized 480×480 targets in this run.
- Retained normalized target ink: **100%** for each glyph.
- Strokes contributing no new ink: **0** across both sheets.
- Eight tests pass: three original overlap tests, two aspect-fit/extraction
  tests, and three smooth-layer tests. Checks cover crossings, hidden future
  arms, complete reconstruction, no ink outside the target, invalid geometry,
  and continuity into the final frame.
- Every target also passes per-sample monotonic reveal and final-composite
  checks. Dependency requirements are unchanged.

These numbers establish compositing behavior, **not segmentation accuracy**.
Exact reconstruction is enforced by design. Pixels outside the original raw
template support are extrapolated into stroke layers rather than omitted;
they account for 2.76% of source ink on average before the old dilation step.
This does not measure the amount outside the new ribbon envelopes.

In enlarged inspection, the side teeth on 月 and 上 and the notch in the long
base of 上 are substantially reduced. Crowded details still have residual
irregularities: the short vertical in 清 is improved but not perfectly smooth,
and some small fragments around 石/泉 remain ambiguous. Some hard turns are
rounded by the ribbon fit. Preserving all ink can assign an unsupported
fragment to an incorrect stroke. Therefore this is an improved automatic
decomposition, not a verified set of calligrapher-authored stroke masks.

The old column uses its original 160×160 mask pipeline; the new one uses
480×480 source crops and ribbon layers. The zero-error claim is relative to
the **new normalized target**, not the original full-resolution generated PNG.
Stroke grouping/order still comes from modern Kai templates. A small set of
manually corrected paths and boundaries is the next useful step for the
remaining difficult junctions.

## Inspect

- [Comparison video](Lishu-Smooth-Strokes.mp4): old animation, new animation,
  and the current isolated new stroke side by side. The rightmost stroke is
  shown complete to make its surface inspectable; the middle column shows its
  animated reveal. Target character is beneath the isolated stroke.
- [Enlarged stroke details](Smooth-Stroke-Detail.png): includes the remaining
  difficulty in 清 alongside clearer improvements in 月 and 上.
- All isolated strokes, old above/new below:
  [heavier sheet](smooth-isolated-reference.png),
  [lighter sheet](smooth-isolated-light.png).
- Complete reconstructions and amplified residuals:
  [heavier sheet](smooth-reconstruction-reference.png),
  [lighter sheet](smooth-reconstruction-light.png).
- [Machine-readable metrics](smooth-metrics.json).

## Reproduce

After the original README's dependency and template setup:

```sh
python3 -m unittest discover -s experiments/stroke-ownership -p 'test_*.py'
python3 -m unittest discover -s experiments/lishu-transfer -p 'test_*.py'
python3 experiments/lishu-transfer/smooth_strokes.py --video
```

Omit `--video` to produce the layers, metrics, and audit images only.
Intermediates are saved in ignored `work/smooth/`. The new experiment reuses
the committed target images; no image-generation call is required.
