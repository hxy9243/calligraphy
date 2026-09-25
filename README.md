# Chinese Calligraphy Animation

Experiments in turning Chinese calligraphy images into ordered stroke animations while retaining their original brush shapes and ink texture.

The latest working prototype uses **separate stroke layers with preserved overlaps**. It animates Wang Wei’s 40-character **山居秋暝** in three generated, artist-inspired styles: Yan Zhenqing, Liu Gongquan, and Zhao Mengfu. The video shows synchronized enlarged characters and the accumulating poem.

This is a reconstruction from static artwork—not recorded handwriting, a verified reproduction of a historical master, or a physical brush/ink simulation.

## Start here: overlap-preserving stroke animation

See the [implementation and detailed guide](experiments/stroke-ownership/README.md).

### Requirements

- Node.js 20+ and npm
- Python 3.10+
- FFmpeg available on PATH
- DejaVu Sans at `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`; on other systems, adjust `fontpath` in the renderer

From the repository root:

```sh
npm ci
python3 -m pip install -r experiments/stroke-ownership/requirements.txt
node experiments/stroke-ownership/ownership_templates.mjs
python3 experiments/stroke-ownership/ownership_prepare.py
python3 -m unittest discover -s experiments/stroke-ownership -p 'test_*.py'
python3 experiments/stroke-ownership/ownership_render.py
```

The normalized artwork inputs and required character data are included. Reproducing this experiment does not require an image-generation service.

Outputs under `experiments/stroke-ownership/`:

- `Stroke-Ownership-Preserved-Overlaps.mp4`: 1920 × 1080, 30 fps, approximately 74 seconds, 3× reference writing cadence, five-second final hold.
- `Stroke-Ownership-Overlap-Audit.png`: source-versus-retained-ink comparisons.
- `ownership-work/`: intermediate stroke masks, registration results, exposure maps, and metrics.

Generated videos and intermediates are ignored by git.

### How it works

1. Start from isolated calligraphy glyphs. Hanzi Writer outlines and median paths provide a prior for stroke topology and order.
2. Register that template to each artwork using smooth optical flow.
3. Keep a bounded mask and progress map for each stroke.
4. **Allow masks to overlap at intersections.** The first participating stroke paints the shared pixels when it reaches them; the later stroke’s arms remain outside that stroke’s mask.
5. Composite the animated layers without double-darkening shared ink.

The first-arrival exposure map is an optimization equivalent to max-compositing the layers with the same ink intensity and reveal ramp. There is no final whole-character reveal to conceal missing regions.

### Why preserve overlaps?

Whole-image brush sweeps can reveal neighboring branches prematurely. An earlier exclusive-ownership experiment prevented that by removing ambiguous pixels, but left visible gaps. The current implementation keeps the independent stroke shapes while restoring their shared intersection areas.

Across the 120 character/style samples:

| Generated style | Ink omitted with exclusive masks | Ink omitted with preserved overlaps |
| --- | ---: | ---: |
| Yan-inspired | 9.88% | 2.16% |
| Liu-inspired | 10.36% | 3.42% |
| Zhao-inspired | 10.91% | 3.37% |

Every stroke retains some ink. These are **retention measurements, not ownership-accuracy scores**. Three regression tests cover shared intersections, hidden future arms, unsupported pixels, and equivalence to layer compositing.

### Current limits and next steps

- Registration can still misassign small regions, particularly in crowded characters.
- Some unsupported ink and tiny disconnected fragments remain omitted.
- Motion is still a reveal within a stroke mask; pressure, brush-tip lag, and physical ink deposition are not modeled.
- The included artwork is artist-inspired AI output, not authenticated historical exemplars.
- The current demonstration has a fixed 40-character layout. Different text requires new artwork/data and layout changes; it is not yet an arbitrary-text generator or mobile app.

Next priorities: manually correct difficult stroke layers, evaluate junction behavior at slower playback, then test continuous brush geometry against the corrected masks. See the [experiment README](experiments/stroke-ownership/README.md) for input formats and reproduction details.

## Earlier experiments

The following baseline demos remain available for comparison. Their render commands use the older template-reveal pipeline, not the overlap-preserving renderer above.

### 永 — brush reveal study

A small, reproducible animation of the Kai-style character 永. The five ordered stroke outlines and median paths are from [Hanzi Writer Data](https://github.com/chanind/hanzi-writer-data), derived from [Make Me a Hanzi](https://github.com/skishore/makemeahanzi). That character data is distributed under the Arphic Public License; see `ARPHICPL.TXT`.

The original stroke geometry is preserved. Each outline is clipped against a moving, broad trace of its median path. The renderer adds a quiet paper surface, stroke-specific timing, pauses between brush lifts, and a leading brush mark. This is a **plausible animation of a static glyph**, not a reconstruction of the calligrapher's actual hand movement or a physical ink simulation.

## View interactively

```sh
npm run serve
```

Open <http://localhost:8000>. Play, pause, replay, and scrub the timeline.
Open <http://localhost:8000/poem.html> for the vertical couplet from Wang Wei's *Mountain Dwelling in Autumn*: 明月松间照，清泉石上流. Each character writes top to bottom, beginning with the right column.

## Export a video

Requires Node.js 20+, npm, and FFmpeg:

```sh
npm install
npm run render
```

The command produces `yong-animation.mp4` (1080 × 1080, 24 fps, approximately 8 seconds). `FPS`, `SIZE`, and `OUTPUT` are optional environment variables.

To export the poem video, run `npm run render:poem`. This creates `poem-animation.mp4` (720 × 1280, 24 fps). `FPS`, `WIDTH`, and `OUTPUT` are optional environment variables.

The poem uses only ten entries in `data/poem-characters.json`; no entire character database is needed. These stroke outlines and medians share the Arphic provenance and license of the 永 example. The renderer is a styled reveal of font geometry, not a reconstruction of a particular calligrapher's handwriting.

To animate different text, edit `LINES` in `src/poem-animation.mjs` and fetch its stroke records with `node scripts/fetch-characters.mjs "your Chinese text"`. The command replaces the poem data file with just the distinct characters in that text. For a separate project, pass a second argument to choose a different JSON output. Then adjust the line/column layout and re-render. Punctuation is omitted from the stroke-data lookup.

See [STYLE_RESEARCH.md](STYLE_RESEARCH.md) for a reference-based style-copy plan and related research.

## Different Kai hands

The [four-hand 書 experiment](experiments/kai-four/README.md) applies one ordered template to four actual regular-script images, retaining the original ink. Watch [`four-kai-shu.mp4`](experiments/kai-four/four-kai-shu.mp4). This test finds that knowing the character and stroke order is enough for a rough replay, but not enough for reliable per-stroke segmentation or believable motion at crossings.

## Annotation and style transfer prototypes

Open the [offline stroke annotator](experiments/kai-four/annotate-standalone.html) to correct the ten proposed 書 stroke masks and paths for each hand. Export the corrected JSON so it can be used as ground truth. See the [annotation guide](experiments/kai-four/README.md).

The [style transfer baseline](experiments/style-transfer/README.md) creates a new 永 from the Yan Zhenqing 書 scan, using the known target strokes with measured optical weight and ink texture. It produces a [still](experiments/style-transfer/yan-inspired-yong.png) and an [animation](experiments/style-transfer/yan-inspired-yong.mp4). Its target geometry remains a generic Kai template; the output is an experimental style approximation.
