# Targeted junction correction follow-up

Starting point: `b34d746` on `experiment/lishu-transfer`.

The automatic ribbon experiment reconstructed the character exactly, but still
left small teeth on 清 and misplaced top-bar ink on 石. This follow-up adds
**four explicit path corrections**: stroke 6 of 清 and stroke 2 of 石 in each
of the two generated sheets. These are agent-authored geometric annotations,
not an improvement claimed to generalize automatically to unseen handwriting.

## Results

- 清's short upper vertical has a straighter edge at its crossings. Clipped
  horizontal-arm ink belongs to the specified horizontal strokes instead of
  being omitted or left as protrusions on the vertical.
- 石's falling stroke no longer contains the detached/misassigned top-bar tip.
  In the lighter sheet its significant core-component count falls from 2 to 1.
- Across **all 20 glyphs**, max-composite pixel error against the normalized
  target remains **0.0**, and every stroke contributes new ink.
- The other **16 glyphs** retain their previous automatic layers unchanged.
- No increase in the number of significant core components was observed on any
  stroke in the four affected glyphs. This diagnostic thresholds ink at 0.5
  and counts components of at least 9 pixels; it is not an aesthetic score.
- **10 regression tests pass**: the previous eight plus tests for pinned
  boundary transfer and invalid controls. Each result also passes monotonic
  reveal, no extra ink outside the target, and final reconstruction checks.

These changes do not establish historical 隶书 stroke correctness. Remaining
small drybrush fragments are not automatically errors, and exact reconstruction
does not establish correct stroke ownership.

## What was rejected

The initial candidate edited 12 paths across 清、泉、石 in both sheets. A
correction to 泉's top turn introduced spikes and was rejected. A later attempt
to straighten its left side made that stroke cleaner but transferred fragments
onto neighboring horizontal strokes. The **whole-character, all-stroke audit**
caught this, so all 泉 corrections were removed from the accepted configuration.
The previous automatic 泉 result is retained and still needs better annotation.

A small residual top-bar component on the heavier 石 was corrected by explicitly
returning it to stroke 1. It was not deleted to make the falling stroke look
cleaner. This is why judging only the edited stroke is insufficient.

## Implementation

[stroke-controls.json](stroke-controls.json) contains the editable controls:

- Sheet name, character, and **1-based stroke number**.
- Ordered `[x, y, radius]` samples in the normalized **480×480** glyph frame.
- Optional junction boxes `[x0, y0, x1, y1]` and the receiving stroke number.
- SHA-256 hashes binding these annotations to the exact source sheets.

The existing automatic and edited paths share one ribbon rasterizer. The new
path supplies an envelope and arc-length progress. All layers remain clipped
to source ink; overlaps still use max compositing.

Coverage normalization can otherwise re-expand a deliberately narrowed stroke.
Inside the annotated junction boxes, the edited boundary is therefore pinned
to its ribbon. If this clips a pixel, its prior alpha is transferred with a
max operation to the named crossing stroke. This preserves the previous union
exactly, including shared intersections, without extra darkness or final fill.
The boxes delimit local corrections; they are not generic character rules.

Unknown sheets/characters, invalid coordinates/radii, duplicate consecutive
points, nonexistent strokes, and invalid recipients are rejected. Source image
hash mismatches stop the runner rather than applying annotations to new art.

## Inspect

- [28.8-second comparison video](Lishu-Junction-Refinement.mp4), 1440×820,
  30 fps. Automatic result, corrected result, and isolated current stroke.
- [Compact before/after detail](Junction-Corrections-Detail.png).
- [Corrected-stroke audit](Junction-Corrections-Audit.png).
- [Every stroke of affected characters](Junction-All-Strokes.png), including
  the strokes receiving reassigned ink.
- [Metrics](refinement-metrics.json), including per-stroke fragment diagnostics,
  contribution checks, control-file hash, and dependency versions.

## Reproduce and edit

Use the setup in the main experiment README. Generate the automatic baseline
first if `work/smooth/` is absent:

```sh
python3 experiments/lishu-transfer/smooth_strokes.py
python3 -m unittest discover -s experiments/stroke-ownership -p 'test_*.py'
python3 -m unittest discover -s experiments/lishu-transfer -p 'test_*.py'
python3 experiments/lishu-transfer/refine_strokes.py --video
```

Omit `--video` for quick audits while editing controls. The runner applies only
the declared corrections and saves layers in ignored `work/refined/`.
Re-review **all** strokes of a changed character, not just the corrected one.
The next useful extension is a visual control-point editor with these checks,
followed by better annotated junctions for 泉; further blind smoothing is unlikely
to resolve its ownership ambiguity.
