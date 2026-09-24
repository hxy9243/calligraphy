# 永 — brush reveal study

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

## Next experiment

Replace the glyph outlines with stroke masks cut from an actual scan, align the existing median paths to the photographed strokes, and retain this animation renderer. A small editor for ambiguous crossings would make that pipeline usable.
