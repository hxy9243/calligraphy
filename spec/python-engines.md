# Python stroke and brush engines

The installed package exports `compose_layers`, `BrushPainter` and `ContactBrush`
from `calligraphy`. Helpers are available from their individual modules. The
models solve different problems; their inputs are not interchangeable.

| Model | Input | Output | Main trade-off |
| --- | --- | --- | --- |
| Overlap layers | Raster supports, per-pixel progress, ink mask | Membership, exposure, owner arrays | Retains source ink; depends on inferred masks |
| Ellipse brush | Path, radius, times and nib settings | Accumulated coverage mask | Compact controls; can round angular/asymmetric forms |
| Contact brush | Paired boundary landmarks and gesture hints | Accumulated coverage mask | Supports asymmetric edges; needs richer geometry |

## Overlap composition

Source: [stroke_layers.py](../calligraphy/stroke_layers.py).

`compose_layers(support, progress, ink, min_component=7)` expects support/progress
shaped `[stroke, y, x]` and ink shaped `[y, x]`. Callers must supply at least one
stroke. Progress must be finite inside support. Supports and ink are converted
to boolean masks; tiny connected components are filtered per layer.

Membership retains shared intersections rather than assigning every pixel to
one exclusive stroke. Arrival is `stroke_index + clip(progress, 0, 1) * 0.88`.
The earliest arrival becomes exposure; unsupported pixels have infinite exposure
and owner `-1`. Owner records the first painter, not exclusive membership.

This allows early strokes to paint shared ink without exposing later arms.
With the same source ink and reveal ramp, earliest exposure is equivalent to
max-compositing the separate animated layers. It avoids darkening an intersection
twice. It does not fix inaccurate supports or restore unsupported source pixels.
Timing here is in stroke-index units, not seconds; presentation runners map it.

## Elliptical footprint brush

Source: [paint_brush.py](../calligraphy/paint_brush.py).

`fit_brush(layer, direction, guide=None)` derives a path, radius and normalized
times from a stroke layer. A supplied guide preserves intended traversal through
turns; otherwise skeleton geometry supplies a path. Fitting smooths widths and
paths, recognizes sufficiently straight strokes, and adds entry/finish timing.
These are geometric heuristics, not measured physical pressure.

`BrushPainter` consumes a record with aligned `path`, `radius`, `times`, plus
`nib_aspect` and `tail_lift` (fitted records also contain `kind`). It deposits
oriented elliptical polygons onto a persistent supersampled canvas. Geometry
must be finite, radii positive and times nondecreasing. Defaults are a 480-pixel
cell and 3× supersampling. Coordinates must agree with the chosen canvas size;
changing size alone does not rescale the input geometry.

## Contact-edge brush

Source: [brush_grammar.py](../calligraphy/brush_grammar.py).

A stroke contains at least three finite `contacts`, shaped `[station, 2, 2]`:
two `[x, y]` boundary points per station. Optional `tension`, `corners` and
`features` influence Hermite interpolation and timing. Paired edges can move
asymmetrically, so contact angle need not follow the centerline normal.

`sample` builds fixed geometric samples and normalized times. Marked corners
zero their tangents; named press/fold/hook features slow local deposition.
`ContactBrush` fills quadrilaterals between successive contact sections. It
never samples a reference image during painting.

`fit_strokes(strokes, target, bound=7.0)` is a separate bounded fitting step. It
fits visible boundaries while reducing penalties for boundaries hidden by other
strokes, regularizes displacement/curvature change and preserves closed tips.
It returns fitted records and reports. Silhouette agreement does not establish
correct historical stroke ownership or motion.

## State, seeking and correctness

Both painters return floating-point coverage masks and accumulate ink on a
persistent canvas. Advance them with finite progress from 0 to 1 in increasing
order. For backward seeking create a fresh painter and replay. ContactBrush
rejects every decreasing progress value; BrushPainter rejects backward movement
of its sample cursor, so callers should not rely on identical validation behavior.
The module-specific `complete(stroke)` helpers paint to 1 with default dimensions.

Sampling geometry is independent of requested video frame rate. Tests check
monotonic coverage, final reconstruction, turns, guide ordering and overlapping
crossings. Read the [Python tests](../tests/python/) when changing fitting or
deposition; also run the relevant retained lab regressions.
