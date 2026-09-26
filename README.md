# Calligraphy

Shared source for reproducible Chinese calligraphy images and writing animations.
The sibling **calligraphy-lab** repository contains experiments, fitting workflows,
reference artwork, comparisons and research videos.

The main repository provides generic Han-text template rendering, two preserved
JavaScript demonstration scenes (永 and a Wang Wei couplet), shared still/video
exporters, and reusable Python overlap, ellipse
brush and contact brush algorithms. These are original style studies and inferred
writing animations, not authenticated historical handwriting or physical bristle
simulation. Arbitrary-text generation in every style is not implemented.

## Render your own text

After `npm ci`, use one command for SVG, PNG or MP4:

```sh
npm run render:text -- --text "明月松间照，清泉石上流" --per-line 5 --output outputs/my-poem.png
npm run render:text -- --text "明月松间照" --direction horizontal-lr --output outputs/my-poem.svg
npm run render:text -- --text "春眠不觉晓" --fetch --output outputs/new-poem.mp4
npm run render:text -- --help
```

Rendering is offline by default. `--fetch` explicitly downloads missing character
records; `--glyphs file.json` supplies a saved dictionary. No network requests
occur while drawing frames. Newlines start columns/rows; supported punctuation
starts a new line by default and is not drawn (`--punctuation omit` skips it
without a line break). Missing glyphs and unsupported text produce explicit errors.

Use `--width`, `--height`, `--per-line`, `--stroke-seconds` and `--gap` to control
the page and cadence. MP4 also accepts `--fps` and `--speed` and requires FFmpeg.
Styles are `kai` (template geometry) and `yan` (the existing measured width
adjustment), not the lab's prepared brush styles.

For programmatic use, `createTextScene({text, glyphs, layout, timing})` returns a
scene for the existing exporters. `createTextPlan()` exposes the geometry-independent
layout/timing contract for future brush adapters. See the
[generic text API specification](spec/generic-text.md) for examples and limits.

## Run the browser examples

Requires Node.js 22.12+ (or a current Node.js 24 release), npm and Python 3.

```sh
npm ci
npm run serve
```

Open <http://localhost:8000/examples/yong.html> for 永 or
<http://localhost:8000/examples/poem.html> for 明月松间照，清泉石上流.
Both examples support timeline playback and seeking.

## Export images and videos

Run from the repository root. FFmpeg must be on PATH for video export.

```sh
# Completed writing as a PNG, or an intermediate frame as SVG
npm run render:still
SCENE=poem TIME=5 OUTPUT=outputs/poem-at-5s.svg npm run render:still

# Videos; low resolution and frame rate are useful for a quick smoke test
FPS=2 SIZE=240 OUTPUT=outputs/yong-smoke.mp4 npm run render:video:yong
FPS=2 WIDTH=360 SPEED=10 OUTPUT=outputs/poem-smoke.mp4 npm run render:video:poem

# Measured Yan-inspired width preset for the poem scene
STYLE=yan OUTPUT=outputs/yan-poem.mp4 npm run render:video:poem
```

`SCENE` selects `yong` or `poem` for still export. `TIME` selects a scene time
in seconds; by default a still shows the completed scene. `OUTPUT` chooses the
file path and, for stills, `.png` or `.svg`. SVG preserves the scene's native
coordinates. `WIDTH`/`HEIGHT` resize PNG output. Video commands accept `FPS`,
`OUTPUT` and `FFMPEG`; the Yong command accepts `SIZE`, and the poem command
accepts `WIDTH`, `SPEED` and `STYLE=yan`. Video dimensions must be even.
The original `npm run render` and `npm run render:poem` aliases are retained.

Images and videos use the same scene frame functions. The Yan preset is a
measured width adjustment to generic Kai geometry; it is not a learned or
historically verified handwriting model.

## Install the Python engine

Python 3.10+ is required. Use a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -c "from calligraphy import BrushPainter, ContactBrush, compose_layers"
```

The package is distributed as `calligraphy-engine` and imported as `calligraphy`.
The lab installs this package rather than maintaining duplicate brush algorithms.
Use the lab README for experiment setup, fixtures and reproduction commands.

## Source layout

```text
assets/                 Supported character data and measured presets
examples/               Browser demos
src/geometry.mjs        Shared path geometry
src/scenes/             Scene composition and timing
src/text/               Input parsing, glyph resolution, layout and writing plans
src/export/             Still export and shared video encoding
scripts/                Thin command entry points and character-data fetcher
python/calligraphy/     Reusable Python brush and overlap engines
tests/                  JavaScript and Python regressions
docs/                   Migration, architecture and research context
```

Start with [the component specifications](spec/README.md) for architecture,
interfaces and design choices. See [the migration plan](docs/migration-plan.md),
[source organization and adding styles](docs/source-organization.md), and
[validation results](docs/validation.md).

## Tests

```sh
npm test
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'
```

The lab retains the original experiment tests. Rendering tests establish
mechanical behavior and regression consistency, not calligraphic authenticity.

## Data and provenance

Character outlines and median paths derive from Hanzi Writer Data and Make Me a
Hanzi. Their Arphic Public License is preserved in [ARPHICPL.TXT](ARPHICPL.TXT).
The measured Yan preset records its experimental source. Historical research
notes are preserved in [docs/research/style-research.md](docs/research/style-research.md).

To fetch a different small character set, run
`npm run fetch:characters -- "your Chinese text" path/to/characters.json`.
The default output replaces the supported poem data, so use an explicit output
path for exploratory data. The generic renderer accepts the dictionary through
`--glyphs`; changing text in the two legacy demos still requires scene edits.

The supported source is published at [hxy9243/calligraphy](https://github.com/hxy9243/calligraphy)
on `main`, with retained Git history. The original `caligraphy` checkout and its
unfinished Lishu worktree are preserved under the local workspace's `archive/`
directory. Research experiments remain in the separate `calligraphy-lab` repository.
