# Working on Calligraphy

- Supported JavaScript lives in `src/`; reusable Python lives in
  `python/calligraphy/`. Keep CLI and browser entry points thin.
- Research runners, fitting studies and generated research evidence belong in
  the separate `calligraphy-lab` repository. Main must not import from lab.
- Preserve character geometry, stroke order, licenses and input provenance during
  refactors. Treat generated style studies and inferred motion as such.
- Use the same scene/frame implementation for still and video exports. Validate
  representative partial frames as well as final images when changing rendering.
- Run `npm test` for JavaScript changes and Python unittest discovery under
  `tests/python` for Python changes. Shared Python changes also require relevant
  downstream lab regressions; see the lab README.
- Do not commit local environments, caches or newly rendered outputs. Stage
  intentional files explicitly and record validation with major changes.

See `docs/source-organization.md` for source ownership and promotion steps.
