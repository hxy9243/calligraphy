# Studio preview display and direction

The studio in `frontend/` uses server-rendered raster images for live font previews and
an export panel for server-rendered previews and completed videos. The export
panel can be opened by generating a preview or selecting an image/video from the
current session's job history.

## Media lifecycle

The export panel owns one persistent image element and a separate inline-SVG
container. Each new inline SVG replaces only the SVG container's content. Showing
an image (including a saved SVG through the history image URL) clears the inline
SVG and reveals the original image element. Repeated SVG/image transitions must
never detach that element or leave the panel blank.

Video playback hides the image/SVG panel. Showing either kind of still preview
or closing the export panel pauses the video so hidden media does not continue
playing. Reopening a saved video reloads its source and attempts playback; normal
browser autoplay restrictions can still require the user to press Play.

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

The live font stage is an editing aid, not a pixel-identical export. Server page
fitting and line wrapping continue to use the shared scene plan, and choosing
horizontal writing does not rotate the page or swap its dimensions.

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
Catalog fonts use their source glyphs; Kai/Yan use the scene renderer. The browser
debounces edits by 800 ms, keeps at most one request in flight and ignores stale
responses. Pending/error status sits outside the artwork viewport. Font cards,
the picker and the selected-font badge use precomputed backend PNG samples of
永, including Kai/Yan. An authoritative missing-glyph response lists the exact
missing characters in an alert near the input and blocks exports until the
text/font changes. These transient previews do not create export jobs or
consume the three-creations-per-minute budget. Exported stills/videos remain
authoritative for inferred brush texture and final layout.

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
