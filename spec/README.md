# Calligraphy specifications

These documents describe the implemented system, its boundaries and the reasons
for its design. They are an onboarding map for humans and agents, not a promise
of features that have not been built. Update the relevant spec with changes to
public behavior, representations or dependency boundaries.

Read in order:

1. [From text to an image or writing video](text-to-render.md)
   — then [Generic text API and writing-plan contract](generic-text.md) for new inputs.
2. [Architecture and component ownership](architecture.md)
3. [JavaScript scenes and export](scenes-and-export.md)
4. [Python stroke and brush engines](python-engines.md)
5. [Promoted contact renderer](contact-renderer.md)
6. [Downloaded fonts to animation](font-preparation.md)
7. [Assets, experiments and validation](assets-and-validation.md)

For runnable setup commands, start with the [repository README](../README.md).
For historical context, see the [migration plan](../docs/migration-plan.md) and
[recorded migration checks](../docs/validation.md). Those reports describe past
runs; the tests and source determine current behavior.

## Where to make a change

| Change | Start here | Read |
| --- | --- | --- |
| Scene composition, text or timing | `src/scenes/` | Scenes and export |
| Shared median-path tracing | `src/geometry.mjs` | Scenes and export |
| Image or video encoding | `src/export/` | Scenes and export |
| Browser controls | `examples/` | Architecture |
| Layer overlap or deposition | `python/calligraphy/` | Python engines |
| Measured supported style preset | `assets/presets/` | Assets and validation |
| Reference fitting study or new style experiment | Sibling `calligraphy-lab` | Assets and validation |

All paths in this table are relative to the repository root unless stated otherwise.
