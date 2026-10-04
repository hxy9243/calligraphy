# Studio preview display

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

## Regression checks

`npm ci && npm test` includes DOM integration tests using jsdom. These tests load
the production `frontend/index.html` and `frontend/app.js`; network and browser
media methods are stubbed. They cover repeated SVG, direct image, history image,
video, close and reopen transitions. They verify DOM identity and visible media
state, not browser rasterization or the actual video decoder.
