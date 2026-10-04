# Workbench web UI

Source: `frontend/` (`index.html`, `style.css`, `js/app.js`, `js/data.js`), served by `backend/app.py`.
The backend API is unchanged.

## Structure
- Three hash-routed views: `#create` (working), `#history` (past jobs), `#fonts` (catalogue).
  Desktop uses a top nav; viewports <= 640px use a bottom tab bar, a fixed action bar and bottom sheets.
- Create flow: 1 text, 2 font, 3 layout, 4 output. Fonts are chosen in a searchable picker
  (category, script, favourites, recents) that previews the user's own text in each face.
- Font entries merge `/api/styles` with `/api/font-catalog`; catalogue-only fonts are also
  exportable because the backend prepares them on demand.
- The stage is a preview only: browser fonts approximate, not reproduce, the engine output.

## Text limits and Layout constraints
- Total character limit: 256 characters (expanded from 120).
- Single-line character limit: 20 characters per line/column. Input validation in both frontend and backend prevents overflowing single lines, prompting the user to break into lines/columns.
- Canvas format & length: Users can select standard format presets (`3:4 标准条幅`, `9:16 修长条屏`, `1:2 加长条幅`, `1:1 正方斗方`, `16:9 横披画幅`) and adjust the main axis canvas length (600px - 1600px). Custom dimensions (`width`, `height`, `direction`) are sent with preview and render requests.

## Result lengths & Framing
- Stage and viewers scroll; "auto-fit" shrinks the stage font (floor 14px) to fit the canvas.
- Result viewers fit by default with comfortable zoom-out framing (88% bounds, padded container) so long vertical scrolls and full video dimensions fit on screen without vertical clipping.
- History cards clamp text, the detail dialog shows full text, parameters and download.

## Persistence
`localStorage` key `wb:v1` keeps draft text, layout, font, recents, favourites, canvas format/length and theme.

