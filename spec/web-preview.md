# Studio preview display and direction

The studio in `frontend/` uses server-rendered raster images for live font previews.
The creation canvas contains only the live layout preview; there is no latest-result tab.
Generated still previews open in a modal. Completed history images/videos open in a
work modal without navigating away from history or changing its filter/search state.

## Media lifecycle

The still-preview modal keeps a persistent image node and a separate inline-SVG
container. Each inline SVG replaces only that container. Repeated SVG/image
transitions preserve the image node. History uses a fresh image/video node per
opening. Videos have native controls and explicit user-started playback, with no
audio autoplay. Closing, replacing, or navigating away pauses and unloads media.

Both work modals use the available viewport height (dynamic viewport units). Video
fits the full media region without the former 420px ceiling. On small screens the
player and its actions fill the initial viewport and job metadata scrolls below.
Native dialog modality, keyboard trapping, Escape, close, and outside-click
controls are supported; dismissal restores focus to the opener when still mounted.

Every completed history video and its detail modal offers an explicit share
control. Creating a link discloses that anyone holding it can view/download that
single video; creating a replacement invalidates its predecessor. Copy fallback
selects the URL for manual copy. Reopening or reloading the same tab validates
and reuses its existing link, preserving the original expiry. The bearer is kept
in sessionStorage (memory-only if storage is denied), never durable localStorage;
it is never displayed until an owner-only status read verifies it. A closed tab
or another browser cannot recover a server-stored secret: the dialog explains
that limitation and labels replacement separately from copying. Explicit
replacement warns that recipients' old links immediately stop working.
Revocation remains available after reopening the share dialog. Links last 72 hours from explicit creation, retaining only that
shared video for that interval. Both creation and copy show the exact expiry and
anyone-with-link privacy notice. The standalone viewer and capability boundary are in `studio-jobs.md`.

## Dark-mode artwork contrast

The rubbing theme keeps dark controls and surroundings, but font badges, picker
and catalog samples, live editor paper, still-output viewers and history
thumbnails/detail viewers use light display paper (`#faf7f0`). Source-font PNGs
contain dark ink on transparent pixels, so they cannot inherit the near-black UI
paper. Artwork is never inverted, brightened with filters, or recolored; changing
the UI theme does not request new pixels or alter downloads. The standalone
shared-video viewer already uses its own fixed light palette.

## Layout direction

The vertical and horizontal buttons select `vertical-rl` (top to bottom, columns
right to left) and `horizontal-lr` (left to right, rows top to bottom). The current
selection drives the live stage and is sent as `direction` in both
`POST /api/previews` and `POST /api/renders`. The browser stores this selection in
local storage under `calligraphy.direction` and restores it on reload. Missing or
invalid saved values default to vertical; blocked storage does not prevent
switching direction or generating exports.

Both request schemas accept exactly these two strings and default to
`vertical-rl` when `direction` is omitted. Unsupported values return HTTP 422
before a job is created. The API persists direction in each job's `params`; the
shared worker passes it into `SceneSpec.layout.direction` for SVG, PNG and video.
Existing jobs without a direction retain the vertical default. Direction changes
create distinct render requests even when their text and style match.

## Editor and export composition

The editor, still and video requests carry the same logical `width`, `height`,
`font_size`, `fit`, spacing, direction and punctuation. Viewport changes only
resize the display. The editor rasterizes the logical page first and downsamples
the completed image to at most 640 pixels per axis, so scaling cannot alter line
breaks, margins, glyph size or brush rounding. Selecting horizontal writing does
not rotate the page or swap its dimensions.

`backend/composition.py` builds the shared `SceneSpec`. Explicit font size keeps
explicit text lines (including punctuation breaks), with no heuristic wrapping
of a single line. All glyph cells use the chosen size; `fit=true` shrinks only
when needed to keep that grid within the shared 7% margin. `fit=false` reports
an actionable overflow error instead of silently clipping or rearranging text.
Requests and older jobs without `font_size` retain the former whole-page fitting
and single-line wrapping. Still/video dimensions continue to default to 720×960.

All studio canvases are bounded to 64–2400 pixels per axis and 3,072,000 total
pixels, covering the existing long-canvas controls. Videos additionally require
even dimensions. This increases the maximum RGB page buffer from 4.9 MB to
9.2 MB; editor transport remains bounded to 640×640 and existing single-job
admission, deadlines, frame counts and video-duration limits remain in force.

Kai/Yan editor pixels use the same completed contact frame as exports. The
lightweight source-font preview keeps source silhouettes, normalized with the
same 480-pixel glyph masks, patch scale, ink/paper colors and placement as the
font export pipeline. It does not fit or register contact strokes on every edit;
inferred stroke-edge texture can still differ from the final still/video.
Cold contact preparation for a 20-character font poem exceeds the editor's
30-second deadline in the serial benchmark, so forcing contact rendering for
this path would regress usable previews. Cached preview identity and active-job
deduplication include logical dimensions, font size and fit.

## Regression checks

`npm ci && npm test` includes DOM integration tests using jsdom. These tests load
the production `frontend/index.html` and `frontend/app.js`; network and browser
media methods are stubbed. They cover repeated SVG, direct image, history image,
video, close and reopen transitions. They verify DOM identity and visible media
state, not browser rasterization or the actual video decoder.

`tests/frontend-direction.test.mjs` verifies request payloads, control state,
reload persistence, defaults and unavailable browser storage. The Python
`test_backend_direction.py` suite exercises the actual endpoints, durable job
params, worker and `RenderPlan` placements for both directions. It stubs glyph
preparation and output encoding; existing renderer/export tests cover those
separately.

## Font privacy

The server mounts only the frontend as static content. `/fonts/*` and
`/data/fonts/*` return 404; the browser never receives source font bytes. Catalog
metadata omits filesystem paths and download URLs. Font tiles and picker glyphs
use fixed server-rasterized PNG samples from `/api/font-samples/{style}`. This
endpoint accepts no arbitrary text or asset paths. `POST /api/editor-preview`
accepts bounded text/layout settings and returns PNG pixels, never font bytes.
Catalog fonts use normalized source glyphs on the shared scene plan; Kai/Yan use the scene renderer. The browser
debounces edits by 800 ms, keeps at most one request in flight and ignores stale
responses. Pending/error status sits outside the artwork viewport. Font cards,
the picker and the selected-font badge use precomputed backend PNG samples of
永, including Kai/Yan. An authoritative missing-glyph response lists the exact
missing characters in an alert near the input and blocks exports until the
text/font changes. These transient previews do not create export jobs or
consume the three-creations-per-minute budget. Exported stills/videos remain
authoritative for inferred brush texture; all paths share logical page layout.

Viewport resizing only adjusts the displayed paper and keeps the current PNG
visible. Mobile browser chrome can resize the viewport while scrolling; this
must not trigger another backend preview or invalidate an in-flight response.
Actual text, font and canvas-setting changes still request new preview pixels.

The ordinary public allowlist and restricted-style guard remain enforced at
catalog and admission. The evaluation deployment explicitly sets
`CALLIGRAPHY_DEMO_ALL_FONTS=1` to include all locally available source fonts.
Source files and license notices remain server-side even in this mode.

First visits start with Traditional Chinese interface copy, initial text and
presets, with the Traditional button active. The Simplified toggle remains
available; explicitly selecting a simplified-only font can convert the text.
Script dictionaries and simplified preset text retain both forms.

The GitHub Star link is the final header control at the far right. A browser
identifying itself with `MicroMessenger` gets a dismissible WeChat advisory once
per tab session: open the site in Safari/Chrome before creating work, because
browser session history does not transfer. It offers URL copying with manual
selection when the clipboard API is unavailable. Detection is advisory only;
it does not disable generation or downloads in any browser.

## Bounded glyph preparation

Kai/Yan editor previews prepare independent uncached glyphs in up to two spawned
processes. The parent retains deterministic input order, stroke order, final
composition and cache identity; duplicate characters are still prepared once.
Only sufficiently large cold work (at least 64 uncached strokes across multiple
glyphs) starts a pool. Warm geometry and smaller requests stay serial to avoid
process-import overhead. Source-font previews retain their lightweight raster
path without contact fitting. This changes preparation scheduling, not glyph geometry or animation.

`CALLIGRAPHY_PREVIEW_WORKERS=1` disables the pool; the default/hard maximum is two.
The editor also reduces this budget for CPU affinity, Linux cgroup CPU quotas,
and small cgroup memory limits. Native math pools in the preview subprocess and
OpenCV threads in fitting children are limited to one. The existing single-editor
admission slot bounds concurrent requests in the deployed one-worker server;
its 30-second process-group deadline also kills fitting descendants. Per-glyph
file locks and atomic SQLite writes preserve shared-cache safety. Failures cancel
queued fits and propagate without publishing a partial preview.

The reusable `create_scene(..., glyph_workers=1)` and `prepare_kai(..., workers=1)`
APIs remain serial by default; video rendering and exports are unchanged.
`scripts/benchmark-preview.py` compares serial and bounded editor subprocesses
with separate cold geometry caches and warm reruns, checking identical PNG hashes.
`test_parallel_preview.py` covers worker budgets, bounded submission, error
cleanup, serial/warm fallback, duplicate reuse and partial/final pixel equality.

See [measured preview validation](../docs/validation-parallel-preview.md) for
cold/warm timings, equivalence checks and environment limits.

`tests/frontend-composition.test.mjs` checks identical editor/still/video logical
payloads, both directions, explicit size/fit and long automatic canvases.
`test_studio_composition.py` verifies actual PNG dimensions, downsampled Kai
pixel equality, source-font/export ink overlap and placement, decoded MP4 partial
and final frames, overflow/area bounds, cache identity and legacy compatibility.
