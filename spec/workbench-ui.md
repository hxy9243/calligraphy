# Workbench web UI

Source: `frontend/` (`index.html`, `style.css`, `app.js`), served by `backend/app.py`.
The backend API is unchanged.

## Structure
- Three hash-routed views: `#create` (working), `#history` (past jobs), `#fonts` (catalogue).
  Desktop (> 960px) uses a viewport-height 2-column layout (compose left,
  preview right), with independent scrolling in each pane. Scrolling controls
  keeps the preview in view; long artwork can be scrolled separately on the right.
  Mobile and narrow viewports (<= 960px) place text input at the very top, followed by live preview, font, layout, and output controls.
  Narrow cards stretch to the available width with explicit 100% bounds. Mobile cards share 12px internal padding; controls, grid tracks and long labels can shrink without widening the page. Chip strips keep their own horizontal scroll, and compact action buttons stay within the fixed bar. The usage note follows output controls rather than preceding text input. Vertical preview paper fits the stage content box after subtracting padding, including widths below 260px; horizontal artwork can still scroll within its stage.
  Viewports <= 640px use a bottom tab bar, a fixed floating action bar and bottom sheets.
- Create flow: 1 text, 2 font, 3 layout, 4 output. Fonts are chosen in a searchable picker
  (category, script, favourites, recents) that previews the user's own text in each face.
- Font entries merge `/api/styles` with `/api/font-catalog`; catalogue-only fonts are also
  exportable because the backend prepares them on demand.
- The stage is a preview only: browser fonts approximate, not reproduce, the engine output.
- Text presets include poems and excerpts; the standalone 永字八法 preset is no longer
  offered. Users can still type 永, and the font samples and rendering engine keep
  their existing glyph support.

## Default script
- The interface declares `zh-Hant` and starts with Traditional Chinese text, converter selection and preset names/text.
- The font picker and catalogue initially show Traditional-capable fonts (`trad` and `both`). The explicit Simplified and unrestricted filters remain available.
- Font display labels from both API routes use the existing OpenCC Traditional conversion. Search accepts either script, while font IDs, source metadata and artwork text remain unchanged.
- Explicit script/font choices can still select Simplified text. Opening the picker or loading font metadata alone does not convert a draft using the default Kai font.

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
`localStorage` keys `calligraphy.direction` and `calligraphy.favorites` retain writing direction and favourite font IDs. Draft text and other controls remain in the current page; changing the default script does not rewrite saved preferences or history text.


Font selection and history detail/playback dialogs close when a click starts and
ends outside their visible panel. Clicking inside or dragging out keeps the dialog
open. Closing the detail dialog pauses its video; Escape and close buttons remain
available.
