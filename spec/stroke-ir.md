# Experimental Kai stroke IR 0.1 and 0.2

`calligraphy.stroke_ir` is an additive experimental representation for one Kai
glyph. It is deliberately isolated from the supported CLI, style registry and
asset formats while fitting and authoring work establishes whether the shape is
useful.

## Paired-contact geometry (0.2)

The 0.2 program keeps character, script, provenance, ordered strokes, relations,
duration and lift intervals. Each stroke replaces `path`, `profile` and `corners`
with a single geometry object:

```json
{
  "id": "s1", "kind": "heng", "duration": 1, "liftAfter": 0.15,
  "geometry": {
    "type": "paired-contacts",
    "stations": [ [[0.1,0.4],[0.1,0.4]], [[0.5,0.38],[0.5,0.45]], [[0.9,0.4],[0.9,0.4]] ],
    "corners": [], "tension": 0
  }
}
```

Use `schemaVersion: "kai-stroke-ir/0.2"` at program level. Each station contains
both contact-edge coordinates, in the same unit square. There must be 3–64
finite paired stations, a traveling midpoint trajectory and nonzero width.
`corners` are ordered unique station indices; `tension` is in [0,1]. The compiler
multiplies coordinates by 480 and passes geometry to the existing ContactBrush.
The runtime accepts no reference mask, clipping mask or completion image.

This explicit geometry mode preserves asymmetric caps and folds which four width
knots could not fit. It is a bounded contact-sweep description, not a physical
brush model or a learned Kai grammar. The lab fits these edge pairs from known
stroke contours and audits intermediate deposition separately. Station count,
contour source and inferred timing belong in provenance and experiment reports.
The legacy 0.1 mode remains supported for low-dimensional authoring.

## Legacy JSON contract (0.1)

Coordinates are normalized to `[0,1]`, with `(0,0)` at the top left. A program
has this shape:

```json
{
  "schemaVersion": "kai-stroke-ir/0.1",
  "character": "永",
  "script": "kai",
  "provenance": {"source": "authored study", "inferred": true},
  "strokes": [{
    "id": "s1",
    "kind": "dian",
    "path": [[ [0.4,0.1], [0.42,0.15], [0.46,0.2], [0.48,0.25] ]],
    "profile": [
      {"s": 0, "left": 0, "right": 0, "angle": 0},
      {"s": 1, "left": 0.03, "right": 0.02, "angle": 0}
    ],
    "corners": [],
    "duration": 1,
    "liftAfter": 0.15
  }],
  "relations": []
}
```

`provenance` is preserved caller metadata and has no rendering semantics.
Unknown fields are rejected everywhere else, so a misspelled geometry or timing
field cannot be silently ignored.

Each path item is a cubic Bezier segment with four `[x,y]` control points.
Adjacent segments share their endpoint and compile to one continuous contact
gesture. `s` is normalized arc length over the complete multi-segment path.
Profiles include knots at `s=0` and `s=1`; `left` and `right` independently set
the two contact widths. `angle`, in radians, rotates the contact axis relative
to the path's local normal and defaults to zero. `corners` lists strictly
increasing interior `s` positions where the existing contact brush suppresses
its interpolation tangent.

`duration` and `liftAfter` are relative timeline units. A lift advances time but
deposits no ink. Relations are authored declarations: version 0.1 accepts
`cross`, `touch` and `near`, validates their stroke IDs, and does not change
rendering from them.

The validator bounds a glyph to 64 strokes, each with at most 32 cubic segments,
64 profile knots and 64 corners. Contact widths are bounded to one normalized
canvas unit. It requires finite JSON provenance, finite timing, and a path that
travels. It does not infer pressure. Stroke `kind` and all relations are
validated annotations in 0.1; neither changes geometry or deposition.

## Compilation and replay

`validate_program(program)` returns the unchanged program or raises
`ValueError`. Errors identify the glyph and, for stroke content, its stroke ID.

`compile_program(program)` samples by path arc length, always including profile
knots and corners, and returns one current `ContactBrush` input record per IR
stroke. Normalized coordinates and widths are multiplied by the engine's
480-unit base canvas. These records contain `contacts`, `corners`, and the
existing fixed contact-brush tension; they are suitable for
`ContactBrush(record)`.

`render_program(program, progress, size=480)` returns a square `float32`
grayscale mask. Progress is normalized over all stroke durations and lift
intervals and is clipped to `[0,1]`. Replay is stateless: each call rebuilds the
brushes, so backward and random seeks reproduce a fresh replay at the same time.
The renderer inherits `ContactBrush`'s internal sampled deposition window
(`0.025..0.975`) and timing heuristic. Those timings are implementation timing,
not measured historical writing speed. Other output sizes resize the base mask.

Version 0.1 does not integrate this IR with the supported CLI, arbitrary-text
renderer or asset registry.

## Experimental smooth sweep compilation

`calligraphy.stroke_sweep.compile_smooth_program(program)` converts a validated
0.2 program into a frozen `smooth-brush-program/0.1` and a measurement report.
Each source stroke is rendered in isolation, short skeleton branches are pruned,
and the existing brush fitter derives one medial path. If skeleton extraction is
ambiguous, the original paired-contact midpoints are used as a reported fallback
guide. Narrow terminal samples are trimmed deliberately, producing rounded tips.

Pressure uses at most twelve smoothed, positive, shape-preserving knots. Radius
change is bounded per unit path length to prevent narrow interior bulges. The
compiled record contains only path, radius, normalized time, nib aspect and tail
behavior. It contains no source or target mask and rendering performs no target
comparison or clipping.

`validate_smooth_program(program)` checks the explicit schema, finite geometry,
bounds, station counts, monotone times, brush parameters, timing and relations.
`render_smooth_program(program, progress, size=480)` performs deterministic,
stateless replay through the existing `BrushPainter`. The same function serves
complete and partial frames. Reports include radius/width roughness before and
after, normalized centre displacement, trimmed endpoint distance and fallback
use. This is a geometric elliptical sweep, not a physical bristle simulation.

## Bounded fitting from an ordered stroke mask

`calligraphy.stroke_fitting.fit_contact_stroke(target480, guide_nx2)` accepts a
connected, hole-free 480×480 boolean stroke mask and a finite unit-square median
ordered entry to exit. It returns normalized paired contacts, equivalent 480px
contacts, and a measured report. Callers must check `report.targetReached`;
fitting returns its best candidate even when IoU remains below 0.95.

The fitter tries 12–64 equally spaced boundary pairs, with a shared 1/3-pixel
boundary correction. If that misses 0.95, `calligraphy.rail_alignment.align_rails`
uses monotone correspondence through concavities and reduces the result to at
most 64 stations. The fitter never supplies a target mask to the renderer.

This mechanism fits a known stroke; it does not infer target stroke ownership
from a whole font glyph, learn an artist's style, or validate historical motion.
The expanded lab study passes 306/306 strokes at 480px. Smaller and larger
rasterizations do not consistently meet that threshold. Preserve this size
qualification when describing the demonstration.

The research runners, external source masks, evaluation and transfer experiments
remain in `calligraphy-lab`. Its compatibility modules import this implementation.
The portable replay demo is in `examples/kai-stroke-ir/`.

### Selective narrow-feature cleanup

`calligraphy.stroke_cleanup.clean_program(program)` returns paired-contact IR
and per-stroke evidence. It applies a small (1–5 canonical pixel radius) opening
to isolated stroke silhouettes during compilation, then reconstructs frozen
contact geometry. Radius derives from stroke thickness, not whole-glyph IoU.
No reference pixels or masks participate in playback. Original IDs, order,
timing, lifts, and relations remain unchanged.

The compiler rejects disconnected cleanup results, more than 12% removed area,
interior holes larger than 25 pixels, or a reconstruction below 86% overlap with
the original isolated stroke. Unsupported strokes remain unchanged with explicit
review flags. Tiny holes may be filled and their area is reported. Narrow
legitimate details may also be shortened; broad ownership errors and physical
brush plausibility remain outside this local contour prior. The lab's selective
viewer compares original, rounded-sweep, and selectively cleaned alternatives.
