# Default generic Kai generation

Generic `kai` uses fitted `kai-stroke-ir/0.2` programs in the Python CLI, Node
`render:text` command and the web preview/video backend. Other font styles and
`yan` retain their existing behavior. `--mode template` in either CLI selects
legacy vector Kai explicitly; `--mode stroke_ir` requires generic `kai`.

Only requested characters are prepared. Hanzi Writer outlines and median guides
are rasterized together using a shared 160px normalization, then fitted at 480px.
Every stroke keeps its original order and gets one scheduled duration, with no
intra-character lift interval. Stroke kinds are marked unclassified rather than
claiming a recovered brush grammar. This is inferred contact motion from guide
shapes, not an imitation of a historical calligrapher.

`prepare_kai` requires final stroke IoU >= .95, monotonic deposition and connected
sampled prefixes. A fit with unsupported topology (holes/disconnected ink), more
than 64 strokes, or a failed gate raises an explicit error. There is no silent
legacy fallback. Missing guide records follow the existing offline/explicit-fetch
policy. The web backend enables guide fetching. Motion checks do not certify
physical writing or guarantee artistic quality; final-terminal overlap is a
recorded diagnostic rather than a gate because strokes can legitimately revisit
previous ink. Scores are measured at 480px, not at every output size.

## Local cache

The SQLite cache defaults to `~/.local/share/calligraphy/kai-geometry.db`.
`CALLIGRAPHY_KAI_CACHE` overrides its file location. Cache names include character,
guide checksum, explicit fitter version and engine source hash. Changing guides
or source code prepares a new revision; previous programs remain exportable using
`python -m calligraphy.artifact_cache --db PATH list` and `export NAME FILE`.

Each program contains producer engine metadata, guide hash and per-stroke fit
reports. Only fully validated glyphs enter the database. Cached programs are
validated again when loaded. Preparation reads no whole font and imports no lab
code. Package installations without Git record a null commit and retain a source
hash; no commit is fabricated.

## Replay and output

`KaiScene` compiles each program once to the shared ContactBrush geometry and uses
existing ContactScene active-stroke deposition and completed-glyph caching.
Backward seek resets active ink. PNG, SVG and MP4 use the same frame function,
page layout, timing, appearance and transforms. SVG wraps the rendered PNG,
which preserves brush deposition rather than presenting it as editable paths.
The stateful scene disables parallel frame generation even when workers > 1.

The web studio defaults to generic Kai when there is no prior explicit selection.
Font browsing still shows the selected font's ordinary text sample; generated
Kai stills and videos come from this shared engine.
