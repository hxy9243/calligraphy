# Generic text rendering

Status: implemented for Hanzi Writer-style template records. The fixed Yong and
poem demos remain unchanged and retain their original frame regressions.

## Public entry points

The npm root exports `createTextScene`, `createTextPlan`, `resolveGlyphs` and
`bundledGlyphs`. The `calligraphy-engine/text` subpath is browser-safe and also
exports `parseText`; it does not import Sharp or child-process APIs.

```js
import { createTextScene, resolveGlyphs, exportStill, encodeVideo } from 'calligraphy-engine';

const text = '明月松间照，清泉石上流';
const glyphs = await resolveGlyphs(text); // bundled records; no network by default
const scene = createTextScene({
  text, glyphs, style: 'kai',
  layout: { width: 1080, height: 1440, direction: 'vertical-rl', charactersPerLine: 5 },
  timing: { intro: 0.5, strokeSeconds: 0.18, characterGap: 0.15, outro: 1 },
});
await exportStill({ ...scene, time: scene.duration, output: 'outputs/text.png' });
await encodeVideo({ ...scene, output: 'outputs/text.mp4', fps: 24, speed: 1 });
```

`resolveGlyphs(text, {glyphs, fetchMissing: true})` explicitly fetches missing
records from Hanzi Writer Data 2.0.1. Fetching is deduplicated and limited to four
simultaneous requests with 15-second request timeouts. Failed or invalid records
reject preparation; the input dictionary is not modified. The result is a plain
dictionary that callers can save. There is no implicit disk cache.

The synchronous scene factory requires complete local geometry. It copies the
geometry it uses so later edits to the input dictionary do not change existing
frames. `glyphs` replaces the default dictionary in the API; the CLI merges its
`--glyphs` file over bundled data for convenience.

## Text policy

Source: [input.mjs](../src/text/input.mjs).

- Preserve character order and repeats. Simplified/traditional forms are distinct.
- Normalize CRLF/CR to newlines. Nonempty explicit lines remain separate.
- Ignore other whitespace, reporting it in `omitted`; it is not a blank glyph cell.
- Default `punctuation: 'break'` uses supported punctuation as line boundaries.
  With `'omit'`, punctuation is skipped without introducing a boundary. Neither
  policy paints punctuation. The supported set is explicit in the parser.
- Reject unsupported characters (including Latin letters and emoji), empty Han
  input and more than 512 Han characters. Do not silently substitute glyphs.
- Report every distinct missing glyph before rendering.

## Layout and schedule

Sources: [layout.mjs](../src/text/layout.mjs), [plan.mjs](../src/text/plan.mjs).

`layout.direction` is `vertical-rl` (top to bottom, columns right to left) or
`horizontal-lr` (left to right, rows top to bottom). `charactersPerLine` controls
wrapping. Otherwise explicit multiple lines remain intact; for a single line,
an aspect-ratio heuristic chooses wrapping. Explicit lines always start new
columns/rows. All glyphs use square cells with uniform scale, centered
as one grid. A shorter line starts at the grid's top/left, not its own center.

Defaults: 1080 × 1440, margin 7% of the smaller dimension, gap 0.18 cell widths.
Pages must have integer dimensions between 64 and 8192, nonnegative margins that
leave room, and a gap between 0 and 2. Cells below 16 pixels are rejected rather
than clipped or silently paginated. This is a single-page renderer.

Timing defaults: 0.5-second intro, 0.18 seconds per stroke, 0.15 seconds between
characters and a 1-second outro. Each character lasts `strokeCount * strokeSeconds`;
there is no trailing character gap. These differ intentionally from the old poem
demo's timing formula. Stroke counts are integers from 1 to 128.

## Interface for brush styles

`createTextPlan({text, strokeCounts, layout, timing, punctuation})` is independent
of glyph shape and renderer. Supply a character-keyed stroke-count dictionary for
the chosen representation, not assumed counts from another style.

Its serializable, frozen result contains:

```text
schemaVersion: 1
text, width, height, direction, strokeSeconds, duration, omitted
schedule[]:
  character, index, line, column, row
  x, y, size                    # square page cell in output pixels
  strokeCount, start, duration, end  # times in scene seconds
```

The template adapter ([text.mjs](../src/scenes/text.mjs)) consumes this plan and
returns `{name, text, style, width, height, duration, plan, schedule, omitted,
frameSVG}`. It assumes canonical Hanzi coordinates, insets each glyph by 4% of
its cell, and uses the existing median-trace/outline-mask approach. Frames are
deterministic and support backward seeking without mutable paint state.

A brush adapter reuses the plan while supplying its own local geometry
and deposition. For a stroke index `k`, local progress derives from
`(time - entry.start - k * plan.strokeSeconds) / plan.strokeSeconds`. Repeated
characters are separate scheduled placements even if they share source geometry.
Stateful brushes must reset/replay for backward seeks. The Node-only `describeContactStyle()` and `renderContactStyle()` bridge now
connects packaged Python contact geometry to the CLI. `createTextScene()` remains
the template SVG factory; the contact bridge accepts a plan and exports PNG/MP4.
See [contact rendering](contact-renderer.md). There is no automatic template fallback for a missing
style-specific glyph.

## CLI and export

`npm run render:text -- --help` lists the full command interface. It accepts
exactly one of `--text` or UTF-8 `--text-file`, then chooses output by extension:
SVG, PNG or MP4. The still defaults to completed writing; `--time` selects a
scene time. Video uses the existing encoder and requires even dimensions.
`--fps`/`--speed` are video-only; `--time` is still-only.

Template styles are `kai` and `yan`; the latter reuses the measured width offset
from the supported preset. The CLI also accepts `lishu`, `liu` and `yan-contact`
using packaged prepared geometry through Python. Contact styles accept PNG/MP4
only. These three fixed banks reject `--fetch` and `--glyphs`. Registered font
styles such as `lishu hanwang` accept those flags to prepare missing characters
through the [font pipeline](font-preparation.md). Punctuation decisions are printed by the CLI, not hidden.

## Validation and remaining limits

[text.test.mjs](../tests/text.test.mjs) covers ordering, repetitions, punctuation,
both layout directions, page bounds, timing, bad configuration, missing/invalid
geometry, scene immutability, partial coverage, offline/fetched resolution, and
real CLI PNG/SVG/MP4 exports. Legacy frame hashes remain unchanged.

Stroke/median shape checks are not a complete SVG-path grammar parser or an
artistic correctness test. The engine does not invent unseen glyphs, synthesize
authentic styles, paginate long documents, paint punctuation or perform general
multilingual typesetting. A successful template lookup establishes renderable
data, not historical correctness of handwriting.

Implementation checks on 2026-09-26: all 28 JavaScript tests passed, including
the 14 legacy checks. A packed installation outside the repository imported the
text API and rendered its bundled glyphs. A live explicit fetch prepared
`春眠不觉晓`; a horizontal PNG was visually inspected and the vertical MP4 was
verified as 320 × 480, 10 frames, 2.5 seconds at 4 fps and speed 4. These smoke
outputs are ignored under `outputs/`; no Python brush algorithms changed.
