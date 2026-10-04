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

## Result lengths
- Stage and viewers scroll; "auto-fit" shrinks the stage font (floor 14px) to fit the canvas.
- Result viewers fit by default with an actual-size toggle; history cards clamp text, the
  detail dialog shows full text, parameters and download.

## Persistence
`localStorage` key `wb:v1` keeps draft text, layout, font, recents, favourites and theme.
