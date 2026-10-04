# Workbench web UI

Source: `frontend/` (`index.html`, `style.css`, `js/app.js`, `js/data.js`), served by `backend/app.py`.
The backend API is unchanged.

## Structure
- Three hash-routed views: `#create` (working), `#history` (past jobs), `#fonts` (catalogue).
  Desktop uses a 2-column layout (compose left, preview right).
  Mobile and narrow viewports (<= 960px) place text input at the very top, followed by live preview, font, layout, and output controls.
  Viewports <= 640px use a bottom tab bar, a fixed floating action bar and bottom sheets.
- Create flow: 1 text, 2 font, 3 layout, 4 output. Fonts are chosen in a searchable picker
  (category, script, favourites, recents) that previews the user's own text in each face.
- Font entries merge `/api/styles` with `/api/font-catalog`; catalogue-only fonts are also
  exportable because the backend prepares them on demand.
- The stage is a preview only: browser fonts approximate, not reproduce, the engine output.

## Text limits and Layout constraints
- Total character limit: 256 characters (expanded from 120).
- Single-line character limit: 20 characters per line/column. Input validation in both frontend and backend prevents overflowing single lines, prompting the user to break into lines/columns.
- Canvas format & length:
  - **Adaptive length (自适应)**: By default, the canvas length (height in vertical mode, width in horizontal mode) dynamically extends based on text character length (up to 2200px/2400px), preserving natural, legible calligraphy cell sizes rather than excessively shrinking fonts.
  - **Manual adjustment (人工调整)**: Users can fine-tune length via the primary axis slider (`600px - 2200px`, 40px steps) or select fixed aspect ratios (`3:4 标准条幅`, `9:16 修长条屏`, `1:2 加长条幅`, `1:1 正方斗方`, `16:9 横披画幅`). A `自适应` chip toggles back to auto mode at any time.
  - Dimension readouts display clean numerical dimensions without redundant status annotations.
  - Custom dimensions (`width`, `height`, `direction`) are sent with preview and render requests.

## Live Stage & Result Framing
- **Real-time stage (实时试写)**: Both `.stage-viewport` and `.stage-paper` automatically lengthen on the web page to fit the artwork naturally without nested inner scrollbox clamping.
- Auto-fit only intervenes if manual canvas boundaries constrain text.
- Result viewers fit by default with comfortable zoom-out framing (88% bounds, padded container) so long vertical scrolls and full video dimensions fit on screen without vertical clipping.
- History cards clamp text; the detail dialog shows full text, parameters, and download options.

## Persistence
`localStorage` key `wb:v1` keeps draft text, layout, font, recents, favourites, canvas format/length, auto-length mode, and theme.

