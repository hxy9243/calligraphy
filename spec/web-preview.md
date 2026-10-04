# Studio preview display and direction

The studio in `frontend/` uses a live CSS text stage for immediate editing and
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

The live CSS stage is an editing aid, not a pixel-identical export. Server page
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
