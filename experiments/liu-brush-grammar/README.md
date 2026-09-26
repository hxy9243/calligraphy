# Liu-inspired brush gesture experiment

This isolated experiment addresses the rounded, warped geometry produced by the
shared elliptical brush. It uses three existing generated Liu-inspired glyphs:
月 (entries, square fold, hook), 千 (horizontal entry, vertical needle), and 人
(falling strokes, spreading finish). It does not modify the shared engine.

## Model

A stroke is an ordered set of **paired contact-edge landmarks**. Unlike a
centerline plus symmetric radius, each edge can move independently. The contact
angle need not be perpendicular to travel. This represents oblique entries,
asymmetric pressing, angular shoulders, hooks, and widening/lifting finishes.

- `contacts`: paired boundary coordinates in a 480 × 480 glyph cell.
- `corners`: landmarks retained as intentional corners, without tangent
  smoothing through the fold.
- `features`: named entry-press, square-fold, hook-turn, finish-press and lift
  landmarks. Press/fold features slow the deposition timing; shape is specified
  by contact geometry, not synthesized from the feature name.
- `tension`: Hermite tangent scale between landmarks.

The painter deposits quadrilaterals between densely sampled contact sections.
Its canvas only accumulates ink. It accepts geometry only: no source-image
clipping, final silhouette replacement, texture copying, or final crossfade.
Full stroke shapes overlap at crossings. Sampling is fixed independently of
video frame rate.

This is a **guided swept-contact geometry model**, not a physical bristle
simulation. It has more shape freedom than the prior ellipse brush, but the
live leading edge is still a geometric cross-section.

## Annotation and fitting

`controls.json` contains manual, image-specific annotations. `make_controls.py`
regenerates those initial annotations. We deliberately corrected a small set of
stroke forms to isolate representation capability from automatic decomposition.
The hidden continuations at crossings remain inferred.

The fitter minimizes signed distance to the source boundary, allowing each
coordinate to move at most seven pixels from its initial annotation. Displacement
and curvature-change penalties regularize the fit. Boundary samples hidden by
other stroke interiors are excluded, so overlapping strokes are retained rather
than trimmed into exclusive ownership regions. Authored point tips stay closed.

`fitted-controls.json` is the replayable result. All fixture arrays and baseline
stroke records are included. The generated reference is an interpretation of
Liu-style regular script, not an authenticated historical exemplar.

## Results

Binary silhouette intersection-over-union at the same 480px alignment and 0.5
threshold (higher is better):

| Glyph | Previous full pipeline | Manual contacts + bounded fitting |
| --- | ---: | ---: |
| 月 | 87.0% | 96.7% |
| 千 | 90.5% | 97.1% |
| 人 | 89.0% | 96.2% |

The comparison visibly retains the entry wedge, angular vertical head, squared
shoulder, and triangular hook that the baseline rounds off. The output remains
very clean and somewhat cut-looking; edge softness, ink variation, and natural
contact-front motion are not solved by this experiment.

These are **in-sample fits**, not calligraphic quality scores or evidence of
automatic style transfer. The comparison changes both annotation and renderer.
No improvement on unseen characters is claimed.

`ablation.py` additionally passes the corrected stroke silhouettes and the
midpoints of their contact landmarks to the old `fit_brush(..., guide=...)`.
That existing fitter/painter retains only 82.1%, 84.9%, and 85.6% IoU to the
corrected full glyphs, respectively. This shows that our existing ellipse fitting
procedure loses shape even with corrected inputs. It is not a proof that every
possible optimized ellipse model must fail; this guide is not optimized for the
old brush. The new contact reconstruction is exact to its own supplied geometry
by construction, so that is not an independent accuracy result.

## Reproduce

From the repository root, using Python 3.10+, FFmpeg, and DejaVu Sans:

```sh
python -m pip install -r experiments/lishu-transfer/requirements-brush.txt
OPENBLAS_NUM_THREADS=1 python experiments/liu-brush-grammar/study.py --video
python experiments/liu-brush-grammar/ablation.py
python -m unittest discover -s experiments/liu-brush-grammar -p 'test_*.py' -v
```

Skip fitting and use the included controls with `study.py --reuse --video`.

Outputs:

- `Liu-Brush-Comparison.png`: same-scale reference / prior brush / new brush.
- `Liu-Brush-Details.png`: enlarged horizontal entry, vertical entry and fold.
- `Liu-Brush-Experiment.mp4`: side-by-side ordered animation.
- `Liu-Brush-Ablation.png`: old model refitted to the same corrected geometry.
- `metrics.json`, `ablation-metrics.json`: measured results.

Five tests check monotonic/frame-rate-independent deposition, connected strokes,
closed tips, bounded fitting, square-fold timing, retained overlaps, and absence
of future arms at a crossing. The video renderer also asserts that the final
accumulated frame exactly equals the new still geometry.

## Next experiment

1. Factor these annotations into normalized reusable entry/shaft/fold/lift
   profiles with width, slant, shoulder depth, and taper parameters.
2. Fit those profiles to additional glyphs with fixed stroke order; report
   held-out performance and annotation effort separately.
3. Improve the advancing contact front and tiny corner rounding without losing
   the fitted final outline. Add ink texture only after that geometry check.
4. Replace manual boundary landmarks with constrained automatic proposals plus
   a correction interface. Keep the current three glyphs as regression fixtures.

Fixtures were extracted from the previous Liu poem experiment's cached targets
and brush output. Their source-pixel hashes are recorded in `fixtures/provenance.json`.
Base revision: `ff68fb462a64456d9f0354b3eee4f86c05cedb9f` (upstream main).
