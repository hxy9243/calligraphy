# Guided brush applied to the Kai study

`paint_brush_kai.py` applies the lishu path/pressure reconstruction to all **120
existing glyphs**: 40 characters in Yan-, Liu-, and Zhao-inspired artwork.
The original source pixels and ordered stroke templates remain the inputs.

Pipeline: registered stroke supports -> smooth overlapping decomposition ->
moderately smoothed isolated outline -> straight or curved brush path -> smooth
pressure -> actual accumulated elliptical footprints. This is an opt-in
geometry renderer; the original source-ink renderer remains available.

Mean silhouette IoU against source artwork: Yan **0.852**, Liu **0.836**, Zhao
**0.840**. Every stroke contributes some new ink, including the tiny dot case
found in Zhao's 來. Similarity is not ownership accuracy: the automatic
decomposition and endpoint-based orientation still need review at difficult
junctions and hooks. The new poem study demonstrates explicit ordered guides
when canonical medians are directly available in target coordinates.

`Kai-Guided-Brush-Comparison.png` compares 清、泉、石 across all three styles,
chosen to match the previous lishu trial. `kai-brush-metrics.json` reports all
120 results. Inputs are the repository's `glyphs.npz` and character templates.

```bash
npm ci
node experiments/stroke-ownership/ownership_templates.mjs
python -m pip install -r experiments/lishu-transfer/requirements-brush.txt
python experiments/stroke-ownership/paint_brush_kai.py
# Optional full 40-character, three-style animation:
python experiments/stroke-ownership/paint_brush_kai.py --reuse --video
```

Use `--resume` only to continue an interrupted run against unchanged inputs;
existing `brush-work/` results are reused. Remove that directory for a clean
rebuild after changing inputs or fitting parameters. It is not committed.

The separately rendered user-requested poem is in `../kaishu-poem/`, using the
same brush with an active path overlay and magnified current-stroke view.
