# Full poem with the contact-strip brush

27 traditional characters, five vertical columns, top to bottom and right to
left, without punctuation, guides, titles or annotations. Light ivory paper,
1080 × 1440, 24fps, 0.28 seconds per stroke, four-second final hold.

Text:

人有悲歡離合
月有陰晴圓缺
此事古難全
但願人長久
千里共嬋娟

Uses `liu-brush-grammar/ContactBrush` for every stroke. 人、月、千 retain the
hand-tuned fitted contacts from that experiment. For the other characters,
canonical stroke templates register to the existing generated Liu reference;
overlapping layers initialize paired contour edges. Monotonic dynamic alignment
pairs the edges, preserving asymmetry and corners, then the same contact-strip
renderer deposits the polygons. There is no fallback to ellipse painting,
source-pixel clipping during animation, or final-character replacement.

This extends the renderer, not a validated automatic Liu brush-style model.
The new automatic contour correspondence and stroke ownership remain inferred;
small isolated fragments can be omitted. The final silhouette metrics do not
validate historical brush movement or semantic stroke ownership. The model
still has clean vector-like edges. Repeated characters reuse their source form.

`targets.npz` retains normalized source glyphs from the preceding Liu poem;
`guides.json` retains the previous inferred paths as ordering guides only.
The source is generated artist-inspired artwork, not a historical facsimile.
`contacts.json` contains replayable fitted geometry for all 25 unique glyphs.

Run from the repository root:

```sh
python -m pip install -r experiments/lishu-transfer/requirements-brush.txt
OPENBLAS_NUM_THREADS=1 python experiments/liu-poem-contact/render.py --video
# Replay the included geometry without rebuilding:
python experiments/liu-poem-contact/render.py --reuse --video
```

The renderer checks that each final animated glyph equals its static geometric
reconstruction. No final-image substitution occurs. Background grain is
procedurally generated with a fixed seed. Outputs are `Liu-Full-Poem-Light.mp4`,
`Liu-Full-Poem-Light.png`, and `metrics.json`.
