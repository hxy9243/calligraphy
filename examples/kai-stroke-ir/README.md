# Kai stroke IR replay example

This is a portable, frozen replay of the 《春曉》 writing demonstration from
`calligraphy-lab/experiments/kai-stroke-ir`. It uses only the installed
`calligraphy-engine` package at runtime. It does not import the lab checkout or
contain its fitting implementation.

The committed poem bundle contains 19 unique fitted glyph programs used by the
20-character poem (處 occurs twice), for 194 ordered strokes. A second frozen
bank contains all 32 study glyphs and 306 strokes, plus the recorded 480px
metrics and SHA-256 of each source fitted program. The programs are reviewable
`kai-stroke-ir/0.2` paired-contact geometry. Generated PNG, MP4, manifests,
inspection frames and caches stay in ignored `work/`.

From the engine checkout, after installing the package:

```sh
.venv/bin/python examples/kai-stroke-ir/render.py frame
.venv/bin/python examples/kai-stroke-ir/render.py frame --progress 0.5
.venv/bin/python examples/kai-stroke-ir/render.py gallery
.venv/bin/python examples/kai-stroke-ir/render.py render --fps 30 --duration 45
python3 -m http.server 8767 --bind 127.0.0.1 --directory examples/kai-stroke-ir
```

Open <http://127.0.0.1:8767/>. `frame` produces a still and manifest. `render`
also streams the same scene frames to FFmpeg to produce `work/writing.mp4`.
The linked 32-glyph inspection page uses the 31 replay frames per glyph produced
by `gallery`; its slider seeks the same deterministic engine renderer.

## Recorded source evidence

The originating development run fitted 32 characters and 306 ordered strokes
from pinned Hanzi Writer 2.0.1 outlines and medians. At its primary 480px
evaluation size, all 306 strokes passed silhouette IoU ≥95%; the minimum was
95.087%, median completed-glyph IoU was 97.527%, and every stroke passed the
boundary p95 ≤2% cell-width gate. The poem subset in this example was selected
from that run rather than refitted in main.

Those results are development evidence, not a held-out benchmark. The expanded
set informed the fitter. Cross-resolution audit results were 254/306 strokes at
240px, 306/306 at 480px, and 188/306 at 960px. Static font-derived outlines and
inferred contact motion do not establish physical brush behavior, stylistic
transfer, or historical handwriting.

The lab remains the canonical home for source masks, fitting configurations,
optimizer logs, comparisons, independent audits, and the 32-character study.
Reusable fitting and replay code belongs in the engine. This fixture snapshot is
an example input so the shipped UI and animation can be reproduced without a lab
dependency.

## Provenance and license

- Poem snapshot source: `calligraphy-lab/experiments/kai-stroke-ir/work/writing/programs.json`
- 32-glyph bank source: fitted programs and concise measurements from
  `calligraphy-lab/experiments/kai-stroke-ir/work/results.json`
- Source study: `calligraphy-lab/experiments/kai-stroke-ir`
- Source records: Hanzi Writer Data / Make Me a Hanzi, version 2.0.1
- Original data license: Arphic Public License; retained as
  [`fixtures/ARPHICPL.TXT`](fixtures/ARPHICPL.TXT)
- Motion claim: stroke order comes from the source records; durations, lifts and
  contact motion are inferred/authored by the study

The lab study is committed at `67bd3d04d8c77a939956218adb79d9690582d508`.
Refresh the bundle deliberately and re-run the engine and lab validation;
do not silently regenerate it during package builds.
