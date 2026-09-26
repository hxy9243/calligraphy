# Contact-brush transfer: Yan-inspired Kaishu and Han-inspired Lishu

Two new full-poem animations use the same contact-strip painter merged in PR #3.
The generated source art changes; the brush implementation and contact-fitting
parameters do not. No Liu-specific manual control points are reused.

Each animation contains the same 27 traditional characters, 245 inferred strokes,
and five columns. Reading/writing proceeds top to bottom, right to left. There
is no punctuation, English annotation, cursor, or guide overlay. Both use the
same light ivory paper with subtle cloud/bamboo decoration and a fine border.

## Generation and replay

`Yan-Source.png`, `Lishu-Source.png`, and `Decorated-Light-Paper.png` were generated
with the built-in image tool. Exact prompts are recorded in `prompts.json`.
They are modern artist/script-inspired interpretations, not historical scans.

The Yan prompt emphasizes broad, weighty regular script associated with Yan
Zhenqing. The Lishu prompt emphasizes flat/wide proportions, silkworm-head entry,
and swallowtail horizontal endings inspired by the Cao Quan stele.

The reference sheets are cropped into 25 distinct glyphs, preserving aspect ratio.
Repeated characters reuse the first source form. Canonical Hanzi Writer stroke
order/topology is registered to each glyph, and overlapping layers initialize
contact edges. Unlike the prior Liu full-poem adapter's cached guides, this
adapter derives ordered guides from the registered per-stroke phase field for
each new source. This is the same style-independent guide method for both trials.

Monotonic contour correspondence produces asymmetric contact pairs, which are
painted by the unmodified `liu-brush-grammar/ContactBrush`. No final source-image
replacement or raster-mask clipping occurs during rendering. The output adapter
reuses the merged poem renderer's exact layout, pace and accumulated-ink checks.

## Results

Macro-average across 25 distinct glyphs, binary silhouette IoU at 480px, 0.5
threshold, aligned to the same normalized source:

| Reference style | Mean IoU | Lowest glyph IoU | Mean source ink coverage |
| --- | ---: | ---: | ---: |
| Yan-inspired Kaishu | 97.38% | 95.87% | 98.22% |
| Han-inspired Lishu | 96.36% | 93.38% | 97.46% |

The completed forms preserve the source-style differences: Yan's heavier upright
structure and rounded entries, versus Lishu's wide proportions and flared tails.
The model transfers well for **final shape reconstruction** in this small test.
These metrics are not style-authenticity, motion-quality, or stroke-order scores.

Lishu exposes more decomposition problems. The minimum per-stroke geometric
IoU to the inferred raster layer is below 0.85 in 歡、離、陰、圓、難、長, versus
only 難 in Yan. Lishu 圓 and 長 include especially weak single-stroke reconstructions
(about 0.51 and 0.56 respectively). This measure is diagnostic only: the inferred
raster layers themselves are not ground truth. The contour initializer takes
the largest connected component, so split/misassigned ink can be omitted even
when other strokes cover it in the finished glyph.

Every stroke contributes new ink. Both complete animations reproduce the static
geometric output exactly before encoding. All 474 unique stroke geometries pass
monotonic, frame-rate-independent replay checks. Each video is 1080 × 1440 at
24fps and lasts approximately 87.17 seconds, including a four-second final hold.

## Reproduce

From the repository root:

```sh
python -m pip install -r experiments/lishu-transfer/requirements-brush.txt
OPENBLAS_NUM_THREADS=1 python experiments/contact-style-transfer/transfer.py --video
# Replay checked-in contacts without registration:
python experiments/contact-style-transfer/transfer.py --reuse --video
python experiments/contact-style-transfer/transfer.py --audit
```

Outputs: `Yan-Kaishu-Poem.mp4`, `Lishu-Poem.mp4`, matching final PNGs, and
`Style-Transfer-Audit.png` (source/reconstruction pairs for six representative
glyphs). `summary.json` and each style's `metrics.json` record the checks.

Next: improve stroke splitting and continuation at Lishu junctions before
claiming equally convincing brush motion. Then add restrained ink texture and
contact-front variation while keeping the final silhouette stable.

## Double-speed exports

`Yan-Kaishu-Poem-2x.mp4` and `Lishu-Poem-2x.mp4` replay all original frames at
48fps, taking 43.58 seconds each. The entire timeline is doubled, including the
final hold. Packet timestamps/durations are halved without re-encoding, so the
compressed frame contents are unchanged. Original 1x exports remain available.

```sh
python experiments/contact-style-transfer/retime.py --speed 2
```

`retiming-2x.json` records before/after frame counts, dimensions and durations.
