# JavaScript scenes and export

Sources: [geometry](../src/geometry.mjs), [scene registry](../src/scenes/index.mjs),
[Yong](../src/scenes/yong.mjs), [poem](../src/scenes/poem.mjs),
[still export](../src/export/still.mjs), [video export](../src/export/video.mjs).

## Scene contract

The registry exposes `getScene(name)` and two entries: `yong` and `poem`.
Each entry has `name`, `duration` (seconds), native `width`/`height`, and
`frameSVG(time, options) -> string`. Yong is 1080 × 1080; the poem is 1080 × 1920.
Unknown scene names throw. The registry is currently fixed, not a plugin loader.

Frames are deterministic functions of time and options: scenes clamp time to
bounds, and paper grain is fixed. Browser scrubbing can request earlier frames
without resetting mutable paint state. Character data contains ordered outlines
and matching median paths. Partial strokes trace median arc length and clip or
mask that broad trace to the outline; completed strokes use the full outline.
This preserves template geometry but does not recover a calligrapher's movement.

`tracePolyline` clamps the requested fraction and returns visited points, a tip
and an SVG path. Coordinates in the path are formatted to two decimal places.
Empty paths are rejected; zero-length segments are handled. It is a geometric
helper, not a full schema validator for arbitrary external input.

## Timing and style

Yong has an authored five-stroke schedule. The poem builds a sequential character
schedule from fixed lines, with per-stroke timing inside each character. Layout
and text currently live in the scene modules. Fetching new character data alone
does not create a new working scene.

`sceneOptions({style, speed})` accepts the `yan` preset or no style. The preset
sets poem outline expansion to `width_offset_px * 4` (currently 16.48); speed also
appears in the poem label. The exporter controls actual playback speed. This
preset is a width adjustment to generic Kai geometry, not a learned style model.
The Yong scene does not apply the poem's style options.

## Still export

`exportStill` takes a frame function, time, output path, dimensions and options.
It writes `.svg` directly or rasterizes `.png` through Sharp. SVG retains native
scene coordinates; width/height resize the PNG. The low-level function defaults
to time zero. The CLI deliberately defaults to scene completion, while explicit
`TIME=0` produces the initial frame.

## Video export

`encodeVideo` samples scene time `i / fps * speed` for
`ceil(duration * fps / speed)` frames, rasterizes each to PNG, and sends them to
FFmpeg through a pipe. It encodes H.264 with `yuv420p`; both output dimensions
must be even. Speed must be positive and at most 10. Sequential writes limit the
number of pending frames instead of retaining an entire movie in memory.

The last sampled time need not equal scene duration. Consequently, sharing a
frame function does not guarantee the final encoded frame equals a still at the
exact endpoint (and H.264 is lossy). Outro holds can keep completed glyphs visible.

Process-start failures, encoder exits and pipe errors reject the operation;
cleanup closes stdin and terminates a still-running child. There is no general
encoding timeout. Existing output files are overwritten (`ffmpeg -y`); failed
exports can leave partial output. Callers should use a fresh output path when
preserving earlier results matters.

## Compatibility and checks

The old `npm run render` and `render:poem` commands remain aliases. Environment
parsing belongs in the CLI scripts; reusable APIs receive explicit values.
See [export tests](../tests/export.test.mjs),
[scene regressions](../tests/scenes.test.mjs) and
[geometry tests](../tests/geometry.test.mjs) before changing these contracts.
