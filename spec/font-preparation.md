# From downloaded fonts to writing animation

Status: implemented for local TrueType/OpenType fonts with Hanzi Writer-compatible
stroke guides. `lishu hanwang` is registered locally from HanWangLiSuMedium.
This is inferred writing motion, not a recovery of the font designer's brushwork.

## Use the registered HanWang style

From the main repository:

```sh
npm run render:text -- --list-styles
npm run render:text -- --style "lishu hanwang" --text "春江花月夜" --output outputs/hanwang.mp4
# Explicitly prepare characters not yet in the bank, then render:
npm run render:text -- --style "lishu hanwang" --text "清風明月" --fetch --output outputs/new-hanwang.mp4
```

Use a PNG output for a still, or `--time 1` for a partial still. SVG is unsupported
by this raster brush renderer. Quote the style name; `lishu-hanwang` is also an
alias for the same local bank. `lishu` still selects the earlier 25-character
collection based on generated reference art.

`--fetch` authorizes downloading missing stroke-order records from Hanzi Writer
Data 2.0.1, followed by local fitting. It does not download a replacement font or
substitute generic character shapes. With all characters prepared, rendering is
offline. `--glyphs records.json` supplies local guides for offline preparation.
A missing font glyph or guide fails explicitly.

## Register a font on another installation

Registration is local user data, not a font bundled into the npm/Python package.
Install the engine and download the lab's pinned HanWang font first:

```sh
# In calligraphy (Node dependencies and FFmpeg are also needed for video):
.venv/bin/python -m pip install -e .
# This verifies the pinned upstream archive and keeps the original license:
.venv/bin/python ../calligraphy-lab/experiments/lishu-font/download.py
npm run prepare:font -- --style "lishu hanwang" \
  --font ../calligraphy-lab/experiments/lishu-font/font/wt021.ttf \
  --license ../calligraphy-lab/experiments/lishu-font/font/license.txt \
  --source https://code.google.com/archive/p/wangfonts/ \
  --text "春江花月夜" --fetch
```

For another downloaded TTF/OTF, supply its path, license file, source URL and a
new lowercase style name. Preparation is proportional to requested characters;
we do not compile an entire font up front. Both the font and the guide source
must cover a character. The 13,068 mapped CJK code points of HanWang are not a
promise of 13,068 automatically correct animations.

An existing style can be extended separately from rendering:

```sh
npm run prepare:font -- --style "lishu hanwang" --text "天地玄黃" --fetch
```

## Pipeline and source ownership

1. `scripts/prepare-font.mjs` parses Han text and resolves ordered outlines and
   median paths. It uses the existing explicit/offline glyph resolver.
2. `src/bridges/contact.mjs` invokes the installed Python package over JSON.
   The npm root exports `prepareFontStyle`, `describeContactStyle`,
   `listContactStyles` and `renderContactStyle`; these are Node-only APIs.
3. `font_pipeline.target_masks` checks Unicode mappings and rasterizes the local
   font. Ink bounds retain their aspect ratio, normalized to a 420px span centered
   on a 480px square. Font side bearings and kerning are not retained.
4. `font_fitting.template` rasterizes ordered guide strokes at 160px. Shared
   affine fitting and optical-flow registration align guide masks and their
   progress fields to the font silhouette.
5. Smooth overlapping ribbons infer per-stroke ownership. Their max composite
   covers the target, but that constraint does not establish semantic correctness.
6. Contour correspondence fits paired boundary rails for each stroke. Disconnected
   components receive separate contact segments with inferred progress intervals;
   they remain one scheduled stroke. This prevents dropping smaller components
   or painting an artificial bridge between them.
7. The registry atomically saves geometry, per-character diagnostics, original
   guide records/hashes and font provenance. No final-font bitmap is substituted
   during rendering.
8. The shared `ContactScene` consumes the normal text plan. `ContactStroke`
   delegates each segment to the unchanged `ContactBrush`. PNG and MP4 sample the
   same frame function; backwards seeks reset/replay the active brush state.

The generic fitter was extracted from the lab's ownership, Lishu registration,
smoothing and contact-transfer studies. It accepts data directly and imports no
lab files. Historical study runners remain reproducible; the lab's new animation
audit imports the installed engine. Core deposition is unchanged for old banks.

## Registry and geometry contract

Default location: `~/.local/share/calligraphy/styles/`. Override with
`CALLIGRAPHY_STYLE_DIR` (a directory, not a JSON filename). Registrations copy the
unmodified font into `fonts/<sha256>.<extension>` and keep its provided license
text and source in the bank. The original downloaded font can then be moved
without breaking new-character preparation.

Names use lowercase letters, digits, spaces and hyphens; spaces/hyphens normalize
to the same filename. Built-in style names are reserved. `--list-styles` shows
registered banks and their prepared counts. A different font needs a different
style name; changing a managed font is detected by its checksum on preparation.

Banks have `schemaVersion: 1`, `pipeline: font-contact-v1`, `font`, `glyphs`,
`templates`, `metrics`, and a geometry checksum verified when loaded. Existing
prepared geometry is reused unchanged. A failed batch leaves the previous bank
intact. A POSIX file lock serializes writers and atomic replacement prevents
readers from seeing a partially written bank. Registered style data and generated
media are not committed to the engine repository.

Plain strokes retain the original `contacts` representation. A disconnected
stroke instead contains `segments: [{start, end, stroke}]`, where
`0 <= start < end <= 1` and `stroke` is an ordinary contact stroke. Intervals can
overlap when inferred phase fields overlap. The stroke count and template order
are unchanged. This structure is an inference, not proof of physical pen lifts.

## Quality and failure policy

Preparation records silhouette IoU, minimum per-stroke IoU against inferred
layers, and strokes contributing no new ink. `review_required` is true for final
IoU below .90, inferred stroke IoU below .75, or any zero-contribution stroke.
The CLI prints affected characters during preparation and rendering; flags do
not silently discard characters or substitute another style. Empty/degenerate
fits fail. Scores above these thresholds do not certify stroke order, motion,
font fidelity at every size, or historical authenticity.

Deposition is monotonic in canonical mask space. Lanczos downsampling can produce
small nonmonotonic edge-pixel changes in RGB output; this is distinct from erasing
paint. Completed replay matches the corresponding directly completed mask.

## Validation

Python tests use a synthetic font to exercise registration, managed font copies,
missing glyphs, invalid guides, checksum tampering, atomic failure, extension,
disconnected segments, monotonic deposition, final replay and backwards seeking.
Node tests run the actual preparation and rendering commands outside the repo,
with a temporary registry and local guides; no network is required.

The HanWang lab audit recomputes scores from the downloaded font and tests replay
for every prepared stroke. Its saved run covers 22 characters / 161 strokes:
mean silhouette IoU 0.975547, minimum 0.959907. A first largest-component-only
fit lost visible ink in 花 and 荒; segment support raised their final IoU to
0.977 and 0.974. Shape comparisons and representative partial frames were inspected.
These are reconstruction checks, not semantic motion annotations.

Checks on 2026-09-26: 32 Node tests passed without skips, 32 working-tree Python
tests passed (including seven pre-existing notebook tests), and all 24 downstream
lab regressions passed. A package built from committed source passed its 25
Python tests in a fresh virtual environment, plus the actual Node font CLI
integration test. Its HanWang PNG matched the development render byte for byte.
The five-character MP4 was verified as 320 × 480, 22 frames, 2.75 seconds at 8 fps
and speed 3. The four-character extension request prepared 清、風、明 and produced
a second MP4. No lab module or original lab font path is required at render time.

## Engine identity and database snapshots

The web API and on-demand font registration share `backend/style_catalog.py`
for catalog-to-registry aliases. In particular, `longcang-xingshu` resolves to
`longcang` and `hanwang-lisu-medium` to `lishu hanwang` on both admission and
first-use preparation. A downloaded catalog font can therefore initialize an
empty local style registry. Existing registrations are reused unchanged;
unavailable or unknown catalog entries are not substituted with another font.

New glyphs carry per-character `glyph_metadata` with engine type/version, Git
commit (when available), dirty state, source-code hash, package version and UTC
preparation time. Extending an old bank does not relabel its existing geometry.
See [geometry caching](geometry-cache.md) for explicit SQLite storage, startup
snapshot import and JSON export. The existing font registry remains JSON-backed.

## Bundled poetry fonts in the Studio

The style selector and font catalog include LXGW WenKai TC, Iansui, LXGW ZhenKai
GB, HanWang LiSu Medium and Qiji before any local fitting bank exists. Selecting
one previews its bundled font face; exports prepare inferred strokes on demand.
Each catalog entry records its own `license_path`, which the worker preserves
in the fitting bank. Four fonts use OFL 1.1; HanWang uses GPL 2 or later.

`data/poetry-fonts.json` records the exact bundled files, family names, versions,
SHA-256 checksums, source projects and coverage audit. All five cover the 250
unique traditional characters in the 18 current UI presets, including excerpts.
This checks code-point mappings, not semantic stroke correctness. Qiji maps some
characters to variant forms; ZhenKai GB uses mainland glyph conventions and
includes AI-assisted additions. Qiji is a Ming woodblock typeface, not Kai.
The original license notices are in `data/licenses/`.
