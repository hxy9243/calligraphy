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

### Derived duplicate-fragment cleanup

The default contact renderer also checks disconnected components in inferred
font strokes. A component smaller than 25% of that stroke's largest component
is removed from its early owner only when at least 99.5% of its binary ink is
already covered by another scheduled stroke's primary component. The covering
stroke retains its own schedule. Primary components cannot delete one another;
whole dots, unique disconnected ink and authored segments are protected from
this additional rule. Existing tiny-satellite cleanup remains separate.

Reports record `removedSatellites`, `reason: covered-by-other-stroke`, the
1-based `ownerStroke`, and measured coverage. The existing combined glyph
retention gate still applies. This repairs duplicated detached fragments, not
connected branches or incorrectly registered guide paths. It is a conservative
ownership inference, not a semantic guarantee for every font.

This runs on derived contacts, so existing registered banks benefit without
refitting or overwriting their source geometry. The engine source hash changes
the derived cache identity. Explicit `font_layers` mode retains its original
decomposition and is not affected by this contact cleanup.

## Reviewed attached-ink ownership

After generic smoothing, inferred contacts for the registered Aa Shou Jin font
have reviewed corrections for 明 stroke 5, 月 stroke 1 and 清 stroke 7. These
are deliberately scoped edits, not automatic branch recognition. The font
SHA-256, original glyph geometry hash and smoothed geometry hash must all match
`contact_ownership.REVIEWS`; changed fits are left untouched with a skipped
report. Authored contacts and explicit `font_layers` mode are unaffected.

Editable rail intervals define the clean donor envelope. Only original pixels
outside that envelope change owners; clipped pixels are reassigned among the
reviewed neighboring strokes by distance. The recipient keeps each pixel's
original alpha, so the union of completed masks must be **exactly equal** before
and after. Source contacts, stroke count, metadata and segment schedules remain
intact. 清 retains its pointed left entry and right terminal.

Derived strokes may carry an `ownership` object with sparse canonical 480×480
pixel records: `clip: [[flatIndex, maxAlpha], ...]` and
`patches: [[flatIndex, alpha, revealProgress], ...]`. Indices are unique integers
in range; alpha and progress are finite in [0,1]. Clipping caps the original
contact deposition; transferred pixels reveal monotonically at the nearest
recipient ink's first sampled solid coverage, alpha ≥ .5 (64 progress steps). This is an
ownership/timing correction, not a newly inferred physical brush trajectory.
It does not solve all residue in these glyphs or generalize to unreviewed fits.

These records live only in the versioned derived cache. The review constants
are Python source and therefore participate in engine source hashing and cache
invalidation. Reports include review version, both geometry hashes, donor,
recipient pixel counts and reveal ranges, and exact final-alpha equality.

## Shared automatic attached-residue cleanup

Every registered font in `auto` and `contact` mode runs
`automatic_contact_ownership.automatic_ownership` after generic crossing
smoothing and any exact-fit reviewed corrections. No font-name allowlist or
per-character controls are used by this automatic pass. Existing registrations
benefit on their next derived-cache miss; their source banks are not rewritten.
Authored built-in contact collections, generic Kai/yan Stroke IR, direct static
font output and explicit `font_layers` reconstruction retain their existing
paths: they are not inferred font-contact ownership inputs.

Candidate detection scales a morphological opening to local stroke width and
looks for short outward excursions in the interior of a predominantly straight
stroke. It protects the first/last 12% of the body, large turns, major area
changes and disconnected pieces. A recipient must have nearby supporting ink;
when multiple neighbors exist, the nearest must beat the next by at least four
canonical pixels. An ambiguous proposal is left unchanged.

Candidates are evaluated in deterministic area order, at most 16 per glyph.
Each participating stroke may receive only one correction in this pass;
reviewed or previously annotated strokes are reserved. This prevents reciprocal
edits and overwriting a receiving stroke's earlier transferred pixels. The
transfer helper explicitly rejects such overwrites.

Before accepting each proposal, the complete accumulated result must retain
exact final alpha and pass 65-step monotonic deposition, completed replay and
partial-glyph connectivity checks. The check spans the earliest through latest
changed stroke, including intervening strokes and previously accepted edits.
New detached components of at least four binary pixels reject the proposal.
Rejected proposals leave the current accepted result untouched.

Reports under `automaticOwnership` record the method version, candidate and
accepted counts, budget deferrals, donor/recipient indices, boundary interval,
owner confidence, transfer details and rejection reasons. Derived clips and
patches use the ownership representation above, shared by still and video
replay. Engine source hashing invalidates old preparation caches automatically.

This is a conservative automatic improvement, not a complete semantic stroke
segmentation system. Small artifacts can remain, checks are sampled, and a
preserved final glyph alone is not evidence of historically correct motion.

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

## Preparation failures

The studio worker preserves a preparation failure (including the font style and
character/stroke cause) in the job error instead of attempting to render an
unwritten bank and reporting it as an unknown font. Missing banks use
`FontBankNotFoundError`, a `ValueError` subtype; invalid existing banks must not
trigger first-use preparation. The scene API catches only that missing-bank
condition when an explicit source font and glyph preparation were requested.

## Compact collapsed-phase strokes

After all normal registration tightness attempts, a surviving compact dot may
use a template-directed principal-axis guide if its progress field collapsed.
This is a bounded relaxation of inferred traversal, not a replacement font or
a dropped stroke: it retains the source-derived contour and schedule position.
Only at least three supported ink pixels spanning no more than 5% of the canvas
dimension qualify; empty/non-finite fields, missing direction, and larger
ambiguous shapes still fail. Disconnected ink keeps separate segments.

Affected strokes carry `guide_inference: compact-dot-template-direction`; their
1-based indices are recorded in `metrics.guide_fallback_strokes` and force
`review_required`. Inferred movement is not certified historical brush motion.
Successful ordinary fits retain their existing geometry and retry ordering.

Successful studio jobs using this compact-dot fallback persist a nonblocking
`warning_message`: 部分細小筆畫使用推估筆路；請檢視成品。 It appears in owner
history, job details and the immediate still-export result, separate from errors. Only requested fallback-marked
glyphs trigger it; loading a previously prepared bank or geometry cache preserves
the warning. A nullable additive database column keeps historical jobs readable
and records the warning from the scene that actually produced that artifact.
