# Stroke ownership with preserved overlaps

An experimental raster-to-stroke pipeline for Wang Wei's 40-character 山居秋暝, compared across Yan Zhenqing-, Liu Gongquan-, and Zhao Mengfu-inspired generated artwork.

## Why overlaps are retained

The first conservative experiment discarded every pixel claimed by multiple stroke supports. It avoided premature branches but left holes and broken strokes. This version keeps a complete bounded mask per stroke, including intersection pixels shared with another stroke. Each layer reveals only its own shape along its own progress map. The first participating stroke paints an intersection when it reaches it; later strokes pass through already painted ink without darkening it twice.

`stroke_layers.compose_layers` computes the first-arrival time as the minimum of the participating layer times. With identical source ink and ramp duration, this is equivalent to max-compositing the animated layers. Unlike globally revealing the finished glyph, a crossing does not automatically reveal the later stroke's arms. Pixels outside every inferred support remain blank; there is no final whole-image fill.

## Run

From the repository root, with Python 3.10+, Node and FFmpeg installed:

```sh
npm ci
python3 -m pip install -r experiments/stroke-ownership/requirements.txt
node experiments/stroke-ownership/ownership_templates.mjs
python3 experiments/stroke-ownership/ownership_prepare.py
python3 -m unittest discover -s experiments/stroke-ownership -p 'test_*.py'
python3 experiments/stroke-ownership/ownership_render.py
```

The renderer uses DejaVu Sans at `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`; install that font or change `fontpath` on other systems.

Outputs under this directory:

- `Stroke-Ownership-Preserved-Overlaps.mp4`: synchronized 40-character, three-style study, 3x reference writing speed and five-second hold.
- `Stroke-Ownership-Overlap-Audit.png`: original/retained ink comparison.
- `ownership-work/`: registered masks, overlapping layer memberships, first-paint owner labels, exposure maps, per-glyph retention metrics, and visual checks. These are ignored by git.

`glyphs.npz` contains the exact 120 normalized grayscale inputs used in the experiment, including replacement glyphs for cropped bottom rows. These are AI-generated interpretations, not scans of historical calligraphy or evidence of authentic artist technique. Generated style references were: broad muscular Yan regular script, lean angular Liu regular script, and supple Zhao regular script. The Chinese text is:

空山新雨後，天氣晚來秋。
明月松間照，清泉石上流。
竹喧歸浣女，蓮動下漁舟。
隨意春芳歇，王孫自可留。

Hanzi Writer data v2.0.1 supplies stroke topology and medians. Its data derives from Make Me a Hanzi/Arphic; see the repository's `ARPHICPL.TXT`. The final ink contours and intensity come from the generated glyph inputs, not generic template outlines.

## Try another set of sheets

Pass `ownership_prepare.py --assets path/to/assets.json`. The JSON maps `Yan`, `Liu`, and `Zhao` to eight-row, five-column grayscale/RGB sheet paths, relative to the JSON. An optional `last_row` points to a three-row, five-column replacement sheet, one style per row. Each sheet must use the same 40 characters and row-major order above. For a different poem, update `TEXT`, fetch its character data with the repository's `scripts/fetch-characters.mjs`, and adapt the grid layout and renderer.

## Checks and limitations

The synthetic crossing tests ensure the intersection appears during the first stroke, future arms remain hidden, unsupported ink is never backfilled, and the first-arrival map matches explicit layer compositing.

Registration uses TV-L1 optical flow to fit per-stroke templates to each artwork. Ownership is still inferred: inaccurate registration can assign a small branch incorrectly. A one-pixel support collar and removal of components smaller than seven pixels remain from the previous experiment. Keeping overlaps fixes the intentional junction holes; it does not establish perfect stroke anatomy.

This remains mask-based animation, not pressure-driven brush deposition. The next useful step is correcting a small set of difficult registered layers manually, then testing continuous brush geometry against those masks.


## Guided brush reconstruction

See [GUIDED_BRUSH.md](GUIDED_BRUSH.md) for pressure-controlled path painting
applied to all 120 glyphs, and [the Kaishu poem study](../kaishu-poem/README.md)
for the active-stroke animation of the requested Su Shi excerpt.
