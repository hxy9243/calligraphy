# Source organization and promotion workflow

## Organizing the final repository

1. Keep reusable JavaScript rendering under `src/` and installable Python
   rendering under `calligraphy/`. Separate scene composition from shared
   geometry, brush deposition and export. Browser UI and command wrappers call
   these engines rather than implementing their own rendering behavior.
2. Keep the browser examples under `examples/`. Supported input data and measured
   style presets belong under `assets/`, with their provenance. Examples are
   concrete working applications, not the location of reusable algorithms.
3. Export static images and animated frames from the same scene representation.
   Keep video encoding separate from frame generation. Preserve the distinction
   between template reveals, raster overlap layers, elliptical footprints and
   contact-edge geometry; they do not have interchangeable artistic guarantees.
4. Put regression tests next to a documented test command under `tests/`. Test
   stroke ordering, partial progress, accumulated ink, preserved overlap, final
   reconstruction and output configuration. Compare representative frames when
   moving rendering code so a directory change cannot quietly alter appearance.
5. Keep study runners, image-specific fitting, notebooks, ablations and evaluation
   evidence in the sibling `calligraphy-lab` repository. The lab depends on the
   main engine. Main must install and run when lab is absent.
6. Track small supported fixtures and existing provenance/license material.
   Ignore new rendered videos, temporary frames, virtual environments and caches.
   Existing committed research outputs remain preserved in the lab; removing
   them from current main does not remove them from historical Git commits.

## Adding a new style

- Start with a lab experiment stating its hypothesis, source provenance, inputs,
  controls and a reproducible invocation.
- Select the appropriate existing representation. Style may affect geometry,
  stroke connection and timing as well as color and width; do not assume every
  style can be expressed by one numeric preset.
- Put candidate reusable algorithm changes in the main package on a branch and
  install it in the lab. Keep experiment-specific fitting and rendering layouts
  in the lab. Compare the candidate against an exact baseline revision.
- Record input hashes, configuration, seed, environment and both Git revisions.
  A dirty editable checkout is useful for development but is not an exact pinned
  release. Mark it as dirty when recording results.
- Promote only the general algorithm and supported data needed by users, with
  tests, examples and limitations. Preserve the experiment and its results as
  evidence. Do not move an entire notebook or study directory into production.

## Limits of the migration

This migration reorganizes existing implementations and shares their real common
parts. It does not establish authentic historical handwriting, automatically
generate arbitrary text in every style, or provide physical bristle simulation.
The Python and JavaScript engines remain distinct backends with different input
models. A future universal writing-plan schema should be based on demonstrated
needs across them rather than introduced as an empty abstraction now.

## Repository history and local development

Both new repositories begin with the original history at `94ccee4`. The lab
also retains the newer merged research history at `d944a6a`. This makes
the split auditable without rewriting the original repository or its linked
worktrees. Their `migration-source` remotes point to the original local checkout;
configure separate publishing remotes when ready to publish. No GitHub repository
has been renamed or created as part of the local migration.

The original `caligraphy-lishu` worktree contains uncommitted Goose poem work.
It remains there unchanged and should be migrated as a separately reviewed lab
experiment when ready. Its environment and generated assets are not silently
added to either new repository.
