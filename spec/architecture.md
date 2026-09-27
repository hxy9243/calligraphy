# Architecture and component ownership

## Scope

Calligraphy supplies reusable rendering code and working demonstrations. It can
export images and videos from generic Han-text template scenes and two preserved
fixed JavaScript scenes, and exposes three Python stroke representations. It does
not yet offer arbitrary-text style synthesis for
all styles, authenticated historical motion, or physical bristle simulation.

## Dependency direction

```text
Browser examples ───────────────> JavaScript scene modules
Command scripts ──> scene registry ──> scenes + geometry + assets
                └─> exporters ──────> Sharp / FFmpeg

Lab experiments ──> installed calligraphy Python package
               └─> installed calligraphy-engine npm package
```

Main must install and run without the lab. Reference preparation, study-specific
layouts and evaluations stay in the lab. It imports the supported engines;
main never reaches into experiment directories for code or configuration.

## Component boundaries

| Component | Responsibility | Boundary |
| --- | --- | --- |
| `src/geometry.mjs` | Polyline distance and partial traces | No scene layout or I/O |
| `src/text/` | Text policy, glyph preparation, layout and writing plans | Network is explicit during preparation; plans contain no glyph geometry |
| `src/scenes/` | Timing, composition and SVG frame generation | No video processes or output files |
| `src/bridges/` | Node-to-Python rendering and font preparation | JSON requests; no lab imports |
| `src/export/` | Rasterization, file writing and encoding | Receives a frame function; does not invent strokes |
| `scripts/` | Environment options and CLI invocation | Keep rendering algorithms out of wrappers |
| `examples/` | Browser playback and seeking | Reuse scene modules |
| `python/calligraphy/` | Overlap and geometric brush algorithms | No experiment asset paths or study-specific CLI |
| `assets/` | Supported input data and measured presets | Preserve provenance and license |

## Design decisions

**Keep JavaScript and Python as separate backends.** JavaScript currently renders
SVG template reveals; Python handles raster layers and geometric deposition.
Their actual input models differ. Sharing algorithms within each backend removes
duplication without forcing an artificial universal writing-plan format.
The [generic text plan](generic-text.md) now shares page placement and stroke-count
timing without prescribing geometry. The Node bridge in `src/bridges/contact.mjs`
passes this plan over JSON to `calligraphy.contact_renderer`, which loads
packaged or locally registered contact banks and exports raster frames. The
[font pipeline](font-preparation.md) prepares new banks from downloaded fonts. See [contact rendering](contact-renderer.md).

**Separate frame generation from output.** A scene can be previewed, exported as
an image or sampled for video using the same geometry. Encoding changes should
not change stroke shape or timing. Python experiment runners still own their
composition and video pipelines; the JavaScript exporter is not a universal
export service for Python.

**Package real reusable code.** Both distributions are named `calligraphy-engine`;
Python imports use `calligraphy`. npm exports are declared in
[package.json](../package.json); Python packaging is declared in
[pyproject.toml](../pyproject.toml). The npm root also exports Node-only exporters,
so browser examples import scene modules directly. Compatibility modules
`src/animation.mjs` and `src/poem-animation.mjs` re-export the organized scenes.

**Preserve behavior during structural changes.** Frame hashes and downstream
fixture comparisons protect the existing output. Deliberate visual changes need
explicitly reviewed new expectations; changing a hash alone is not validation.
