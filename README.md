# Calligraphy

Shared source for reproducible Chinese calligraphy images and writing animations.
The sibling **calligraphy-lab** repository contains experiments, fitting workflows,
reference artwork, comparisons and research videos.

The default rendering engine (`calligraphy/`) and studio backend (`backend/`) are
implemented in Python. The repository includes an interactive web studio
(`frontend/`), generic Han-text fitted Kai rendering, extensible font-derived style
fitting, and reproducible still/video exporters.
JavaScript powers the browser interface and interactive demos. Legacy JavaScript
scene, export and Python bridge APIs remain in `src/`; the default CLI and studio
do not require a Node server.

## Quickstart and Installation

Python 3.10+ is required. Set up a virtual environment and install the package:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

The package is distributed as `calligraphy-engine` and provides the `calligraphy` CLI
command (as well as `python -m calligraphy.cli`). FFmpeg must be on PATH for video export.

Node.js is optional for the Python CLI and studio. Install Node dependencies to
use legacy JavaScript export APIs or develop and test the browser code:

```sh
npm ci
```

## Render your own text

Use the unified `calligraphy` command to generate SVG, PNG or MP4:

```sh
calligraphy --text "明月松间照，清泉石上流" --per-line 5 --output outputs/my-poem.png
calligraphy --text "明月松间照" --direction horizontal-lr --output outputs/my-poem.svg
calligraphy --text "春眠不觉晓" --fetch --output outputs/new-poem.mp4
calligraphy --help
```

*(Note: `npm run render:text -- ...` is also configured to delegate to this Python CLI).*

Rendering is offline by default. `--fetch` explicitly downloads missing character
records from Hanzi Writer Data; `--glyphs file.json` supplies a saved dictionary. No network
requests occur while drawing frames. Newlines start columns/rows; supported punctuation
starts a new line by default and is not drawn (`--punctuation omit` skips it
without a line break). Missing glyphs and unsupported text produce explicit errors.

Use `--width`, `--height`, `--per-line`, `--stroke-seconds` and `--gap` to control
the page and cadence. MP4 also accepts `--fps` and `--speed` and requires FFmpeg.
Generic `kai` defaults to fitted Stroke IR with per-character SQLite caching.
All web previews and videos default to the smoothed contact engine, including
registered fonts. Derived repairs are cached separately from source font banks,
keyed by font, geometry and engine source. `CALLIGRAPHY_CONTACT_CACHE` overrides
the derived cache location. Existing font banks receive repairs on first use.
`--mode template` selects the legacy Kai/Yan vector renderer; `yan` retains its
measured width adjustment before fitting. Contact SVG contains embedded rendered pixels;
use template mode for editable vector paths. Prepared
contact-brush styles are `lishu`, `liu` and `yan-contact`, supporting PNG and MP4:

```sh
calligraphy --text "人有悲歡離合" --style lishu --output outputs/lishu.png
calligraphy --text "人有悲歡離合" --style liu --output outputs/liu.mp4
```

Each contact style covers 25 prepared traditional characters; missing characters
produce errors. These are inferred style studies, not arbitrary-text synthesis.
See [the contact renderer specification](spec/contact-renderer.md) for coverage,
provenance and measured reconstruction quality.

For programmatic use in Python:
```python
from calligraphy import create_scene, SceneSpec, export_still, export_video
scene = create_scene(SceneSpec(text="明月松间照", style="kai"))
export_still(scene, "output.png")
```

For programmatic JavaScript use in the browser, `createTextScene({text, glyphs, layout, timing})`
and `createTextPlan()` expose the geometry-independent layout/timing contract shared by
template and contact-brush adapters. See the [generic text API specification](spec/generic-text.md).

## Animate a downloaded font

Registered extensible font styles include **`longcang`** (LongCang-Regular.ttf under SIL OFL 1.1)
and **`lishu hanwang`** (HanWangLiSuMedium). After one-time registration, render or prepare
additional characters explicitly:

```sh
calligraphy --list-styles
calligraphy --style "longcang" --text "春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少。" --per-line 5 --output outputs/chunxiao-longcang.mp4
calligraphy --style "lishu hanwang" --text "春江花月夜" --fetch --output outputs/hanwang.mp4
```

To prepare and register a font without immediate rendering:

```sh
calligraphy --prepare-only --style "lishu hanwang" --font data/fonts/HanWangLiSuMedium.ttf --license data/licenses/WangFonts-GPL.txt --text "春江花月夜" --fetch
```

The pipeline fits ordered contact strokes to the font's shapes and caches them;
subsequent renders are offline. See [font preparation](spec/font-preparation.md)
for font registration details, setup commands, and quality limits.

## Kai stroke programs and replay demo

The [Kai stroke IR](spec/stroke-ir.md) validates and renders ordered
contact geometry through the shared brush. `calligraphy.stroke_fitting` prepares
bounded contacts from known stroke masks. The [portable Kai demo](examples/kai-stroke-ir/README.md)
replays the 32-character study and 《春曉》 without depending on the lab checkout.
Its 95% shape results are measured at 480px, not guaranteed at every output size.

## Run the Web Studio and API

The studio backend is a FastAPI service with asynchronous worker rendering and
SQLite storage. The engine installation above does not install the studio's
server dependencies.
From the repository root, with the virtual environment activated:

```sh
# Install the additional studio dependencies
pip install fastapi 'uvicorn[standard]' 'pydantic>=2,<3'

# Start the studio API and static web UI
uvicorn backend.app:app --reload --port 8000
# or via npm alias:
npm run serve:api
```

Open <http://localhost:8000> to interact with the studio in the browser.
Still previews execute synchronously; video requests enter the SQLite-backed
background queue. See [studio jobs](spec/studio-jobs.md) for job ownership,
deduplication and browser status behavior.

For the static legacy browser examples (永 and poem couplet):

```sh
python3 -m http.server 8000
# or: npm run serve
```
Open <http://localhost:8000/examples/yong.html> or <http://localhost:8000/examples/poem.html>.

## Export images and videos

Run directly with Python from the repository root:

```sh
# Completed writing as a PNG, or an intermediate frame as SVG
calligraphy --text "永" --output outputs/yong.png
calligraphy --text "明月松间照，清泉石上流" --per-line 5 --time 5 --output outputs/poem-at-5s.svg

# Videos; low resolution and frame rate for a smoke test
calligraphy --text "永" --fps 2 --width 240 --height 240 --output outputs/yong-smoke.mp4
calligraphy --text "明月松间照，清泉石上流" --per-line 5 --fps 2 --width 360 --height 480 --speed 10 --output outputs/poem-smoke.mp4

# Measured Yan-inspired width preset for the poem scene
calligraphy --text "明月松间照，清泉石上流" --per-line 5 --style yan --output outputs/yan-poem.mp4
```

Video dimensions must be even numbers. FFmpeg must be installed and on PATH.

## Animation pipeline and OpenCV

The default Python pipeline is:

```text
Text + style + settings → character geometry → layout and writing schedule
                       → contact-brush frames → PNG/SVG or FFmpeg MP4
```

`SceneSpec` in `calligraphy/spec.py` describes the request. `create_scene()` in
`calligraphy/renderer.py` resolves the style and prepares or loads ordered strokes.
`calligraphy/text/layout.py` places characters; `calligraphy/text/plan.py` assigns
writing times. Generic Kai/Yan uses fitted Stroke IR; built-in contact styles use
prepared collections; registered fonts combine font silhouettes with canonical
stroke guides. Font-derived motion is inferred, not recovered historical brushwork.

`calligraphy/styled_contact_scene.py` assembles each frame through the shared
contact brush. Completed characters reuse cached masks; the active character
deposits ink progressively. Backward seeks reset and replay the active painters.
Still and video exporters use the same frame implementation.

OpenCV (`opencv-python-headless`, imported as `cv2`) supplies shape analysis and
raster drawing operations:

| Functionality | Main module | OpenCV operations |
| --- | --- | --- |
| Extract stroke boundaries and check connected ink/holes | `calligraphy/stroke_fitting.py` | `findContours`, `contourArea`, `connectedComponents` |
| Preserve disconnected pieces of a font-derived stroke | `calligraphy/font_pipeline.py` | `connectedComponentsWithStats`, `dilate` |
| Locate crossing regions and check repair connectivity | `calligraphy/stroke_crossings.py` | `dilate`, `connectedComponents` |
| Paint contact strips and downsample supersampled coverage | `calligraphy/brush_grammar.py` | `fillPoly`, `resize` |
| Alternative elliptical brush and experimental contour cleanup | `calligraphy/paint_brush.py`, `calligraphy/stroke_cleanup.py` | `fillConvexPoly`, `approxPolyDP`, `morphologyEx` |

The default `ContactBrush` paints successive quadrilaterals on a 3× canvas, then
downsamples the accumulated ink mask for smooth edges. Pillow handles page
composition and font rasterization; scikit-image supplies optical-flow alignment
and skeleton extraction; SciPy handles interpolation and optimization; FFmpeg
encodes video. Stroke order comes from the supplied guides.

## Source layout

```text
calligraphy/            Reusable Python rendering engine, brush algorithms, geometry, layout, and CLI
backend/                Python FastAPI server, database and async background worker
frontend/               Web studio single-page application (browser UI)
assets/                 Supported character data and measured presets
examples/               Interactive browser demos
src/                    Legacy JavaScript scene modules and compatibility bridges
scripts/                Command entry points and helpers
tests/                  Python and JavaScript regression test suites
docs/                   Architecture, migration plans, and research context
```

Start with [the component specifications](spec/README.md) for architecture,
interfaces and design choices. See [the migration plan](docs/migration-plan.md),
[source organization and adding styles](docs/source-organization.md), and
[validation results](docs/validation.md).

## Tests

```sh
# Python regression test suite
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'

# JavaScript regression test suite (optional)
npm test
```

## Data and provenance

Character outlines and median paths derive from Hanzi Writer Data and Make Me a
Hanzi. Their Arphic Public License is preserved in [ARPHICPL.TXT](ARPHICPL.TXT).
The measured Yan preset records its experimental source. Historical research
notes are preserved in [docs/research/style-research.md](docs/research/style-research.md).

To fetch a small character dictionary to a JSON file:

```sh
python -m calligraphy.text.glyphs "明月松间照清泉石上流" assets/data/characters.json
# or:
calligraphy --text "明月松间照清泉石上流" --fetch-to assets/data/characters.json
```

The supported source is published at [hxy9243/calligraphy](https://github.com/hxy9243/calligraphy)
on `main`, with retained Git history. The original `caligraphy` checkout and its
unfinished Lishu worktree are preserved under the local workspace's `archive/`
directory. Research experiments remain in the separate `calligraphy-lab` repository.
