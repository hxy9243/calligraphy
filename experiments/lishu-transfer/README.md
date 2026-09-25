# Kai → 隶书: image and animation transfer experiment

Latest: [explicit smooth Bézier outlines](SMOOTH_OUTLINES.md) test a geometry-first
alternative on 清、泉、石. See [comparison video](Lishu-Smooth-Outlines.mp4)
and [outline overlays](Outline-Comparison.png). This mode trades exact source
pixels and texture for smooth boundaries; the previous mode remains unchanged.

Previously: [targeted junction corrections](JUNCTION_REFINEMENT.md) improve 清 and
石 with four explicit, editable path controls. Watch the
[focused comparison](Lishu-Junction-Refinement.mp4). All 20 normalized targets
still reconstruct exactly; corrections that made 泉's neighboring strokes worse
were rejected.

## Follow-up: smooth individual strokes

The branch already contains current main `4e2a972`; main was checked again
before this follow-up and had not advanced. The first experiment only improved
registration, leaving hard raster-mask boundaries. The new
[smooth-stroke experiment](SMOOTH_STROKES.md) fits continuous stroke ribbons,
preserves overlapping intersections, and reconstructs every normalized target
pixel through the stroke layers themselves.

Watch [Lishu-Smooth-Strokes.mp4](Lishu-Smooth-Strokes.mp4), or inspect
[enlarged individual strokes](Smooth-Stroke-Detail.png).

The original registration experiment and its results follow below.

**Result: promising with one small registration adaptation; the unchanged
pipeline is unreliable on wider clerical forms.** This is an experiment on
20 generated glyphs (two versions of the same ten characters), not a measured
general success rate or a verified reconstruction of clerical handwriting.

Branch: `experiment/lishu-transfer`, based on main
`4e2a9722b0995da977faf8fde2a7d55316d5bbf7`. Production files are unchanged.
See the pre-run [plan](PLAN.md), [metrics](metrics.json), and
[comparison video](Lishu-Transfer-Comparison.mp4).

## What was tested

Text: **明月松間照，清泉石上流**. We reused the existing Yan-inspired
artwork and Hanzi Writer stroke data from `../stroke-ownership`.

1. **Reference-conditioned, heavier ink:** the built-in image generator rewrote
   the source sheet into clerical-inspired forms, with the text and cell order
   fixed. [Prompt](prompt.txt), [input](source-kai.png),
   [output](target-lishu.png).
2. **Text-only, lighter ink:** a separate call emphasized broader, lower forms
   and restrained principal flared endings without supplying the source image.
   [Prompt](prompt-light.txt), [output](target-lishu-light.png).
   This is a generation control, not a second reference-conditioned transfer.

The first target preserves more source weight. The second has more pronounced
horizontal proportions. Visual inspection finds the ten intended identities
readable in both, including traditional 間. No OCR or calligrapher validation
was performed. These are generated, Cao Quan-inspired interpretations; no
authenticated rubbing or historical stroke annotation was supplied. Naming a
style in a prompt is not evidence of faithful attribution.

## The adaptation

The baseline calls main's `ownership_prepare.process` without modification.
The experimental path first fits the template's ink bounding box to the target
independently in x and y. It transforms masks **and progress fields together**,
then uses exactly the same optical-flow parameters, support threshold,
one-pixel dilation, small-component removal, and overlap-preserving compositor.

This changes registration initialization, not the target artwork. There is no
extra dilation, nearest-stroke ink assignment, final whole-character reveal,
or hand-corrected mask. Images retain their native aspect ratios during
normalization to 160×160. Cell cuts can move into nearby whitespace so flared
ends aren't clipped at a nominal grid boundary.

## Measured results

Percentages below are mean **source ink intensity retained**, averaged equally
across ten characters. They are not stroke-ownership accuracy.

| Artwork | Unchanged | Aspect fit | Empty layers, unchanged → fit | Strokes with no first-painted pixels, unchanged → fit |
|---|---:|---:|---:|---:|
| Existing Kai control | 97.84% | 97.84% | 0 → 0 | 0 → 0 |
| Reference-conditioned 隶书 | 95.64% | 98.04% | 1 → 0 | 2 → 0 |
| Lighter 隶书 | 87.20% | 96.75% | 9 → 0 | 10 → 0 |

The last column also catches a nonempty stroke whose entire mask has already
been exposed by earlier strokes. Both adapted sheets pass the provisional
95% mean-retention/no-empty-layer gate in the plan. Their worst characters
retain 97.56% and 96.05%, respectively.

The mean glyph ink-box width/height increases from 0.95 in the Kai source to
1.47 and 1.93 in the two targets. This is a shape descriptor, not an authenticity
score. It helps explain why a global proportion correction is effective.

### Concrete failures and improvements

- **上:** the baseline retains 84.84% of the heavy target and just 38.99% of
  the light target. In the light target it loses the final horizontal layer
  entirely. Aspect fitting retains 97.96% / 96.24% and restores the long base
  stroke. In the heavy baseline, part of that base appears prematurely with
  the first vertical stroke; fitting substantially improves that junction.
- **石:** baseline retention is 87.86% / 76.10%, versus 98.35% / 96.68% after
  fitting. The light baseline loses two layers.
- **照:** light-baseline retention is already 96.36%, yet all four final dot
  layers are empty: some dot ink gets exposed by earlier, wrongly registered
  strokes. This is a direct example of high retention hiding bad animation.
  Fitting restores all four layers (96.67% retention).
- **流:** stroke 4 is empty in both baselines and present after fitting.
- **清:** the baseline's last layer contributes no new pixels on both targets;
  fitting restores a contribution, though crowded intersections still need
  close review.

Inspect [heavy stroke boundaries](strokes-reference.png) and
[light stroke boundaries](strokes-light.png). Each pair of rows compares
baseline / aspect fit at the end of every stroke for 月、間、清、泉、上.
Full target / baseline / adapted / omitted-red / owner-color audits:
[Kai](audit-kai.png), [heavy](audit-reference.png), [light](audit-light.png).
Owner colors show the first painting stroke, not all overlapping memberships.

## What remains unsolved

- Small shoulder/junction protrusions still reveal with neighboring strokes,
  visible around the inner horizontals of 月 and upper strokes of 泉. Discrete
  boundaries do not prove smooth motion between them.
- The retained artwork looks clerical-inspired, but its animation inherits
  modern regular-script topology and order. Hook treatment, stroke grouping,
  and historical ductus are unverified. No claim of correct 隶书 penmanship.
- Both targets were generated with isolated glyphs and familiar characters.
  New radicals, historical variants, actual rubbings, connected brushwork,
  and arbitrary text remain untested. The two generations are not an
  independent statistical benchmark; no success probability is estimated.
- 160×160 analysis loses fine drybrush texture. Roughly 2–4% of ink remains
  omitted in adapted targets, including thresholded faint edges and unsupported
  fragments. None is silently filled at the end.
- Geometry fitting alone is not a style generator. It makes an existing
  clerical image easier to animate; the image generator created the style.

## Reproduce

From repository root, using the existing Node/Python/FFmpeg requirements:

```sh
npm ci
python3 -m pip install -r experiments/stroke-ownership/requirements.txt
node experiments/stroke-ownership/ownership_templates.mjs
python3 -m unittest discover -s experiments/stroke-ownership -p 'test_*.py'
python3 -m unittest discover -s experiments/lishu-transfer -p 'test_*.py'
python3 experiments/lishu-transfer/experiment.py --video
```

No image-generation API is needed for reproduction; both original target
sheets are committed. Omit `--video` for metrics/audits only. Re-running writes
outputs in this experiment directory and intermediates into ignored `work/`.
The renderer uses DejaVu Sans at the same Linux path as the main experiment.
`metrics.json` records dependency versions and input SHA-256 hashes; image
regeneration is not deterministic and no seed was exposed by the built-in tool.
Stroke data retains the repository's Arphic provenance/license.

Video: 1440×900, 24 fps, 78.83 seconds. Columns show target, unchanged pipeline,
and aspect fit with synchronized timing, heavy sheet first and light sheet
second. Each character has an initial blank pause and each sheet a final hold.

Validation completed: the three existing overlap tests and two new affine /
cell-extraction tests pass. All 60 character-method cases pass monotonic reveal,
finite supported exposure, unsupported-pixel exclusion, and exact final-mask
checks. Export dimensions, frame rate and duration were checked with FFprobe;
sampled video frames and stroke-boundary contact sheets were visually inspected.

## Recommended next experiment

Keep this branch as the reviewable evidence. Before promoting aspect fitting
into main, evaluate a held-out set with more radicals and genuine licensed
clerical exemplars. Manually annotate masks and paths for roughly 5–10 hard
glyphs, then measure per-stroke overlap, premature-arm exposure, and direction
against those annotations. For historical variants, supply a clerical-specific
stroke prior rather than forcing a modern Kai decomposition. Increase analysis
resolution after ownership is checked, and then tune pressure/speed at flared
endings for more convincing motion.
