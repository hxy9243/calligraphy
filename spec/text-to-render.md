# From text to an image or writing video

The new [generic text API](generic-text.md) accepts text and builds layout and
timing automatically: `createTextScene({text, glyphs, layout, timing})`, or
`npm run render:text -- --text "明月松间照" --output outputs/text.png`.
Glyph data still determines the shapes; the Python lab studies use prepared,
style-specific geometry. Both need more than a Unicode string to draw ordered
strokes. The worked example below describes the preserved fixed poem demo;
its timing and placement rules are not the generic API's defaults.

## 1. Text identifies the glyphs we need

In [the poem scene](../src/scenes/poem.mjs), the current input is:

```js
const LINES = ['明月松间照', '清泉石上流'];
```

Each string is a vertical column. Characters remain in reading order; repeated
characters produce repeated placements even though they can share glyph data.
The first column is placed on the right and written top to bottom, then the
second column on the left.

This is a developer-edited constant, not a user-facing text box. The Yong scene
is a separate fixed one-character composition with its own authored timings.

## 2. Resolve characters into ordered stroke geometry

[fetch-characters.mjs](../scripts/fetch-characters.mjs) is an optional preparation
step. It takes text, retains unique Han characters, fetches their records from
the pinned Hanzi Writer Data 2.0.1 CDN path and writes a local JSON dictionary.
Punctuation and non-Han characters are omitted by this fetcher. It checks for
stroke arrays with a matching number of medians and fails if fetching fails.

Each character record contains:

- `strokes`: ordered SVG paths describing the filled outline of each stroke.
- `medians`: matching ordered polylines describing travel through those strokes.

An outline answers **what shape should this stroke have?** A median answers
**in what direction should it appear?** The array order supplies stroke order.
These are template data, not live predictions from an AI model.

The scene imports [its saved dictionary](../assets/data/poem-characters.json).
Rendering itself does not fetch data or call an image-generation service. It
looks up each character and rejects missing records or mismatched stroke/median
counts when constructing the schedule. This is not exhaustive geometry validation.

The scene does not apply the fetcher's punctuation filtering: putting punctuation
directly into `LINES` would try to look it up as a glyph and normally fail.
Simplified and traditional forms are distinct keys; there is no conversion step.

## 3. Place glyphs and assign writing times

The poem scene constructs a schedule containing the character, its data, column,
row, start time and duration. Its current rules are:

- Wait 1.15 seconds before writing.
- Give a character `0.70 + 0.175 * strokeCount` seconds.
- Divide that time equally among its strokes.
- Leave a 0.19-second gap after each character, then add an outro.
- Round the total scene duration up to a whole second (currently 26 seconds).

For example, the saved **明** has eight strokes. It writes for 2.10 seconds,
starting at 1.15 seconds and finishing at 3.25 seconds. Each stroke has 0.2625
seconds; the next character starts at 3.44 seconds.

Glyph placement uses fixed column positions and row spacing, with a scale and
vertical-axis flip to place the glyph coordinates on the SVG page. There is no
automatic line wrapping or page fitting. All columns after the first currently
use the same left-column position, so adding a third line requires layout work.

## 4. Build the picture for a particular instant

`poemFrameSVG(time, options)` creates an SVG document. For each stroke it computes:

```text
progress = clamp((time - characterStart - strokeIndex * strokeTime) / strokeTime, 0, 1)
```

At progress zero it draws nothing. Between zero and one it traces that fraction
of the median's arc length, draws a broad line along the trace and masks it to
the stroke outline. At one it fills the complete outline. Earlier strokes stay
visible while later strokes have not yet appeared.

For **明** at 1.50 seconds, the first stroke is complete and the second is about
one-third through its median; the remaining six have not started. This is a
fraction of travel distance, not a promise that one-third of its ink area is shown.

The page also contains paper, fixed grain, titles and progress indicators.
Calligraphy glyphs are SVG paths; ordinary labels use font text. Frame generation
is deterministic and stateless, so preview controls can seek directly to a time.

The JavaScript `STYLE=yan` option expands the poem's generic stroke geometry using
a measured width offset. It does not select the lab's Yan contact-brush model,
invent new character forms or switch the scene to a Python renderer.

## 5. Choose image, preview or video output

```text
Fixed text + saved glyph records
             ↓
       Placement and schedule
             ↓
       SVG frame at time t
          /     |      \
   Browser     SVG     Sharp rasterization
                       /             \
                     PNG       PNG frames → FFmpeg → MP4
```

- Browser examples display the requested SVG frame during playback or seeking.
- Still export writes SVG directly or uses Sharp to rasterize it into PNG.
  The CLI defaults to the completed scene; `TIME` requests an intermediate frame.
- Video export samples scene time `frameIndex / FPS * SPEED` and passes raster
  frames to FFmpeg. It does not have a separate stroke drawing implementation.

For an existing scene, from the repository root:

```sh
SCENE=poem TIME=1.5 OUTPUT=outputs/poem-partial.png npm run render:still
SCENE=poem OUTPUT=outputs/poem-complete.svg npm run render:still
OUTPUT=outputs/poem.mp4 npm run render:video:poem
```

See [scenes and export](scenes-and-export.md) for dimensions, defaults and video
sampling limits. A compressed video's last frame need not equal the endpoint
still pixel-for-pixel.

## How the Python style studies differ

In the lab's `experiments/liu-poem-contact/render.py` and
`experiments/contact-style-transfer/transfer.py`, text still determines character
lookup, reading order and page placement. A preparation stage creates the shapes:

```text
Reference artwork + canonical stroke templates + guides/manual controls
                 ↓
       Align and separate overlapping strokes
                 ↓
       Prepare per-character contact geometry
                 ↓
       Text looks up those prepared glyphs
                 ↓
       ContactBrush deposits ink over time
                 ↓
       Compose the page → still or video
```

The contact renderer reads saved `contacts.json` records, paints each stroke's
paired boundary geometry and max-composites the coverage. Reference images help
prepare the geometry; the brush does not copy source pixels while painting.
Repeated characters reuse the same prepared form, with fresh painters for each
placement. These study runners own their composition and export code.

Other studies use raster overlap layers or elliptical brush footprints; see
[Python engines](python-engines.md). These are alternative representations, not
consecutive stages that every render passes through. New text needs prepared
geometry for every required character; a style name alone cannot supply it.

## Changing the input

For the generic JavaScript path, supply new text to the API/CLI and provide or
explicitly fetch any missing glyphs. It handles layout, wrapping and timing.
See [the generic spec](generic-text.md) for punctuation and page-size policies.

For the two legacy demos only, prepare records for the exact characters, update the
scene's `LINES` and imported dictionary, and adjust placement, labels and counters
to the new content. The current counter is fixed at ten characters. Fetch into
a separate output file when experimenting to avoid replacing the supported data.
Then review both partial and completed frames and run relevant regressions.

For a Python style study, also supply appropriate reference glyphs or authored
brush controls, rerun the study's preparation and review its inferred strokes.
Existing input-specific controls do not generalize automatically to new glyphs.

The generic template feature now supplies an explicit API, punctuation and
missing-glyph policies, and adaptable layout. Obtaining new style-specific brush
geometry remains separate preparation work. The main CLI now integrates the
prepared contact renderer for `lishu`, `liu` and `yan-contact`; see
[its pipeline and coverage](contact-renderer.md).
