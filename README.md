# 永 — brush reveal study

A small, reproducible animation of the Kai-style character 永. The five ordered stroke outlines and median paths are from [Hanzi Writer Data](https://github.com/chanind/hanzi-writer-data), derived from [Make Me a Hanzi](https://github.com/skishore/makemeahanzi). That character data is distributed under the Arphic Public License; see `ARPHICPL.TXT`.

The original stroke geometry is preserved. Each outline is clipped against a moving, broad trace of its median path. The renderer adds a quiet paper surface, stroke-specific timing, pauses between brush lifts, and a leading brush mark. This is a **plausible animation of a static glyph**, not a reconstruction of the calligrapher's actual hand movement or a physical ink simulation.

## View interactively

```sh
npm run serve
```

Open <http://localhost:8000>. Play, pause, replay, and scrub the timeline.

## Export a video

Requires Node.js 20+, npm, and FFmpeg:

```sh
npm install
npm run render
```

The command produces `yong-animation.mp4` (1080 × 1080, 24 fps, approximately 8 seconds). `FPS`, `SIZE`, and `OUTPUT` are optional environment variables.

## Next experiment

Replace the glyph outlines with stroke masks cut from an actual scan, align the existing median paths to the photographed strokes, and retain this animation renderer. A small editor for ambiguous crossings would make that pipeline usable.
