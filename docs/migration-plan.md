# Calligraphy source and experiment migration

## Baseline and scope

Source: `/home/kevin/Workspace/caligraphy`, commit `94ccee4`.
Destinations: sibling repositories `calligraphy` and `calligraphy-lab`.
Both retain the existing Git history; no history rewrite or remote publication.
Original source and the dirty `caligraphy-lishu` worktree remain intact. Its
uncommitted Goose poem work is not silently incorporated into the supported engine.
The local `migration-source` remote records provenance, not a publishing destination.

## Ordered milestones

1. **Record the plan and baseline.** Inventory tracked source, dependencies,
   experiment inputs and tests. Run existing tests before editing.
2. **Extract experiments and reusable Python engines.** Keep all six experiment
   directories and their tracked assets in the lab. Promote reusable overlap
   compositing, elliptical brush and contact brush code into an installable Python
   package in the main repo. Lab scripts import that package through compatibility
   adapters; do not keep independent copies of promoted algorithms.
3. **Organize the main JavaScript source.** Put demos under `examples/`, shared
   geometry/rendering/export code under `src/`, and command entry points under
   `scripts/`. Share the video encoder, retain the existing visual output, and add
   still export using the same frame functions. Move the Yan preset out of the
   experiment directory. Preserve supported environment variables and document
   any new paths.
4. **Complete the split and documentation.** Remove experiments from the main
   working tree only after verifying their assets exist in the lab. Document
   setup, architecture, adding styles, lab dependencies and experiment promotion.
   Keep existing assets and attribution. Ignore future generated outputs.
5. **Validate and record results.** Run main and lab unit tests, compare fixed-time
   baseline frames, render small PNG/video samples, inspect dimensions and duration,
   and test from outside repository CWD. Independently review imports, packaging,
   asset preservation and dependency direction. Commit fixes and final validation.

Each major milestone is a local commit. Stage explicit files only. Agents own
disjoint code areas; the coordinator sequences commits in the main repository.

## Final ownership

Main: `src/` (JavaScript engine), `python/calligraphy/` (Python engine),
`assets/` (supported data/presets), `examples/` (browser demos), `scripts/`
(CLI adapters), `tests/`, `docs/`, and dependency manifests.

Lab: `experiments/` (runners, fixtures, recorded evidence), `scripts/`
(test/setup helpers), dependency manifests, migration provenance and documentation.
Experimental registration, fitting workflows and study-specific layouts remain
experimental. A common interface does not make different brush models equivalent.

Dependency direction: lab -> installed main package. Main must run without lab.
For local development use an editable install; for recorded runs capture exact
main and lab revisions and working-tree status. No hardcoded developer paths.

## Acceptance criteria

- All tracked experimental inputs, controls, metrics and media are preserved.
- Main has no runtime imports from `experiments/` or the old checkout.
- Promoted algorithms have a single implementation; existing study behavior and
  regression tests survive through imports/adapters.
- Deterministic SVG frames match the original at representative timestamps.
- Still and video export use the same scene/frame implementation.
- Unit and smoke-test results are reported honestly, including baseline failures
  and missing historical artifacts; visual fidelity is not claimed from tests alone.
- Original dirty worktree is unchanged, and both destination repos are clean after
  final commits.
