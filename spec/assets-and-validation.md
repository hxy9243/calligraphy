# Assets, experiments and validation

## Supported data and provenance

`assets/data/` contains the small character sets used by the supported scenes.
Outlines and median paths derive from Hanzi Writer Data / Make Me a Hanzi; retain
[ARPHICPL.TXT](../ARPHICPL.TXT) with redistributed glyph data. The npm package
allowlist includes runtime assets and that license.

`assets/presets/yan-inspired.json` retains measurements and the originating
experiment/commit. Only its width offset drives the current poem expansion;
other measurements are provenance, not implemented rendering controls. Describe
outputs as studies or inferred animations, not verified historical reproductions.

`scripts/fetch-characters.mjs` can replace the default poem data. Use an explicit
output path for experimental character sets. Preserve outline/median ordering
and validate the scene's actual text after changing its input.

## Lab boundary and promotion

The sibling `calligraphy-lab` owns research runners, image-specific fitting,
reference sheets, controls, ablations and recorded evidence. It installs the
main Python and npm packages. Compatibility adapters preserve older study
commands while importing the single supported algorithm implementation.

For a new experiment:

1. State the hypothesis, inputs, provenance, configuration and reproduction steps.
2. Use a main-engine branch for reusable algorithm changes; keep study-specific
   preparation and evaluation in lab.
3. Compare against an exact baseline. Record both repository revisions, dirty
   state, actual installed package location, input/config hashes and seeds.
4. Promote reusable code and the minimal supported assets with tests and a
   working example. Preserve the original study and results in lab.

The lab's `core-version.json` records a validated engine revision. Editable
installs track local changes; they are not automatically pinned to that revision.
Its run-metadata helper distinguishes the installed package from the sibling
checkout. Refer to the lab README for current setup and helper commands.

## Validation by component

| Change | Relevant validation |
| --- | --- |
| Geometry or scene refactor | `npm test`; compare partial and completed SVG frames |
| Export path or encoder | Export tests plus small real PNG/video and FFprobe checks |
| Python fitting/deposition | Main Python tests plus affected lab regression suites |
| Packaging | Fresh npm packed install / Python wheel install outside repo directories |
| Reference or preset | Check provenance, data ordering and intended visual difference |

Main commands after dependency installation:

```sh
npm test
.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'
```

For the lab, run `PYTHON=.venv/bin/python npm test` from its root after installing
its dependencies. Test counts and successful past runs are recorded in
[validation.md](../docs/validation.md); do not assume those counts remain fixed.

Frame hashes intentionally detect formatting as well as visual changes. A hash
failure needs investigation, not automatic replacement. Tests of monotonic ink
and reconstruction establish mechanical correctness; human inspection is still
needed to judge motion, style and ambiguous crossings.

## Storage choices

Ignore environments, caches and new generated media. Retain small supported
fixtures and existing historical evidence. Large new research outputs should
have a deliberate storage/provenance plan rather than enter main by default.
The migration preserved Git history: separation of current source does not
remove old experiments or videos from historical objects.
