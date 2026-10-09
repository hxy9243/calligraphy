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

`prepare_kai` targets final stroke IoU >= .95 but accepts fits at or above .90,
with monotonic deposition and connected sampled prefixes still required. Keeping
the higher fitting target avoids degrading successful existing fits merely to
meet the lower rejection threshold. Producer provenance records both thresholds;
per-stroke `targetReached` still reports whether the 95% target was achieved.
A fit with unsupported topology (holes/substantial disconnected ink), more
than 64 strokes, or a failed gate raises an explicit error. A narrow rasterization
exception permits satellites totaling at most 8 pixels, strictly less than 1% of
the main component, with every satellite pixel within 3 pixels of that component
at 480px. Only contour extraction ignores these tiny satellites; all IoU scores
and subsequent smoothing checks use the full original target. Per-stroke reports
record input component count, ignored pixel count and maximum distance. This
handles detached antialiased tip pixels (such as 闕 stroke 10) without loosening
single-brush connectivity or silently deleting substantial disconnected ink.
There is no silent legacy fallback. Missing guide records follow the existing offline/explicit-fetch
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

## Crossing-aware body smoothing

After fitting, `stroke_crossings.smooth_kai_program` repairs local rail dents and
protrusions where another stroke crosses the body. This ports the Lishu study's
crossing-local interpolation to Kai; the Kai policy preserves authored corners
and the first/last two contact pairs. It does not apply Lishu's straight internal
bar rebuilding or hidden-tip extension to Kai. No character-specific rules are
used, and unrelated concavities are retained.

The proposal must preserve stroke connectivity and the original overlap graph,
retain at least 97.5% whole-glyph IoU, and pass 31 sampled monotonic/connected
prefix checks for changed strokes. Default preparation additionally requires
90% IoU against each original guide stroke after smoothing, matching the
pre-smoothing acceptance floor. This allows deliberate repair of guide-boundary defects
hidden at crossings, while the complete character retains at least 97.5%.
Failure keeps the original glyph;
`provenance.crossingSmoothing` records the proposal, acceptance and reason.
`fitReports` continue to describe the pre-smoothing fit; the smoothing report
contains post-proposal target scores. This remains inferred geometry, with
no guarantee that every crossing defect is identified. Existing frozen examples
are not rewritten. The engine source hash invalidates stale preparation caches.

### Fitted-corner and satellite policy

`inferred_corners=True` distinguishes automatically fitted contour markers from
explicitly authored corners. Within a transverse crossing, a marker may be removed
only when the surrounding centerline directions agree (cosine > .95), the local
body stays close to its chord, and existing displacement/shape/connectivity guards
pass. The crossing interval includes a 20px collar so its interpolation anchors
sit outside the bump. Generic preparation uses this inferred policy; direct
`smooth_kai_program` calls preserve authored corners unless explicitly opted in.

`smooth_kai_contacts` also handles the font pipeline's segmented contacts without
changing scheduled stroke count. A detached component is classified as fitting
debris only if it has at most 128 canonical pixels and less than 1% of the largest
component of that same stroke. Entire dot strokes and substantial disconnected
pieces are retained. Surviving segment progress intervals are unchanged. Removals
are recorded in `removedSatellites`; the complete proposal still requires .975
retention. This intentionally permits removal of tiny disconnected components;
it is not a general deletion rule for disconnected handwriting.
