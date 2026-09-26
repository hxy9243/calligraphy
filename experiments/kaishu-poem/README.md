# Kaishu poem with an active brush guide

Requested text (27 characters, 245 strokes, punctuation preserved):

```text
人有悲歡離合，
月有陰晴圓缺，
此事古難全。
但願人長久，
千里共嬋娟。
```

`characters.json` contains the 25 distinct traditional characters from Hanzi
Writer Data **2.0.1**, fetched from
`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/{character}.json`.
The stroke outlines derive from Make Me a Hanzi / Arphic; see the repository's
`ARPHICPL.TXT`. This is regular-script template geometry, not a newly generated
artist-style painting or a historical calligrapher's handwriting.

The same pressure-controlled brush used in the lishu experiment now accepts an
explicit ordered centerline. This study supplies the canonical stroke medians
as guides, preserving hook order instead of choosing direction solely from
skeleton endpoints. Width, initial press, turns and lift use the shared fitter.
Ink is accumulated from elliptical brush footprints; it is not clipped to the
template and no finished character is substituted into the animated frame.

The portrait animation shows the five lines as they are written, an ochre active
centerline and moving tip, plus magnified current-character and isolated-stroke
views below. The guide disappears after each character; the final poem is clean.
The reconstruction is approximate: thin tips and some turns differ from the
templates. Every stroke contributes new ink in this test.

## Run

```bash
python -m pip install -r experiments/lishu-transfer/requirements-brush.txt
python experiments/kaishu-poem/render.py --video
# Re-render without rebuilding brush paths:
python experiments/kaishu-poem/render.py --reuse --video
```

Requires FFmpeg and DejaVu Sans, as the existing experiments do. No CJK font,
network call, image generation or earlier work cache is required to reproduce.

Outputs: `Kaishu-Poem-Guided-Brush.mp4`, `Kaishu-Poem-Final.png`, `metrics.json`,
and temporary `work/` brush parameters. Metrics compare binary silhouettes with
the source templates and do not establish calligraphic quality.

Validation: 19 lishu/stroke-ownership tests pass, including ordered-hook and
compact-dot regressions. The renderer checks that each completed character is
exactly the accumulated brush union; all 27 characters are rendered in supplied
order with their original line breaks and punctuation.
