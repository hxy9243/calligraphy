# Migration validation

Validation performed on 2026-09-26 by the coordinating agent and independent
GPT-5.6 Sol agents using medium reasoning. This records observed behavior, not a
claim of calligraphic authenticity.

## Baseline

- Core source: `94ccee489f7cb079ea9a1b5beda2ee8e388d562c` in the original
  `caligraphy` checkout, which was clean before migration.
- Latest already-merged research: `d944a6a` from that checkout's cached
  `origin/main`. Its additional contact-style-transfer study is retained in lab.
- Original Python suites: **24 passed** (3 overlap, 16 Lishu, 5 contact brush).
- All 9 original tracked JavaScript modules passed syntax checks.

The original Lishu worktree has uncommitted Goose poem files and an environment.
It was not renamed, cleaned or edited. Keeping the original Git directory also
preserves its linked-worktree metadata.

## Main engine

- `npm ci` succeeded; `npm test`: **14 passed**, including geometry, scene
  baselines, still export, encoder failure handling and an FFmpeg smoke export.
- Installed Python package tests: **12 passed** under
  `python -m unittest discover -s tests/python -p 'test_*.py'`.
- Committed SVG regression hashes cover Yong at 0, 1.25, 4 and 8 seconds;
  the poem at 0, 1.5, 10 and 26 seconds; and the Yan preset at 10 seconds.
  They match the original source exactly.
- Independent comparison additionally matched both default SVG scenes at 11
  boundary/interior timestamps per scene with unchanged durations.
- Independent Python comparisons matched overlap arrays, fitted ellipse brush
  records and masks, all 9 contact fixture stroke masks, and rasterized outlines.
- A packed npm install imported successfully from outside the repository. Its
  package contains required character JSON, the style preset and ARPHICPL.TXT.
- A fresh isolated Python installation imported from `site-packages` while
  running outside the repository with `python -I`. A built wheel contains only
  the four engine modules and package metadata, with no lab dependency.
- Main runtime source has no imports from lab or the original checkout.

## Render inspection

Small real exports were inspected with FFprobe:

| Artifact | Dimensions | Duration | Frames |
| --- | --- | --- | --- |
| Yong smoke video | 240 × 240 | 8 seconds | 8 |
| Accelerated poem smoke video | 270 × 480 | 3 seconds | 3 |

Final Yong and Yan-preset poem PNGs were visually inspected: full glyphs, clear
layout and expected paper/background treatment. These low-frame-rate videos
exercise encoding and timing; they are not a perceptual review of full-speed
brush motion. Browser interaction was not manually exercised in this migration.

Local ignored outputs are retained under `outputs/migration-validation/`.

## Lab validation after extraction

- A fresh virtual environment installed `calligraphy-lab/requirements.txt`.
  `PYTHON=<venv>/bin/python npm test` passed **24/24** retained regressions.
- The restored Lishu `paint_brush.py --help` entry point works. In a temporary
  copy, its regenerated comparison image and metrics matched original SHA-256
  hashes exactly.
- The contact-style-transfer Yan `--reuse` render, also run in a temporary copy,
  reproduced the original PNG hash exactly.
- Run metadata reports the real installed engine location and editable-install
  provenance, the matching sibling checkout, its revision and working-tree state.
- All 32 lab Python source files parsed and all lab JavaScript modules passed
  syntax checks. The migration did not regenerate tracked research artifacts.

## Asset preservation

`migration-assets.json` records SHA-256 hashes for all **170** original experiment
files across eight folders at the latest merged research revision. All paths
were preserved in lab; **108** data/media assets matched byte-for-byte. Expected
source changes are import adapters, setup and documentation updates. Git history
preserves the original source implementations.

## Known limitations

- The existing Sharp dependency remains at the original 0.34 series to avoid
  combining a rendering-library upgrade with this structural migration. Its npm
  audit reports a high-severity advisory; dependency remediation remains separate
  work and should include render regressions.
- This split shares reusable algorithms without pretending the raster overlap,
  elliptical brush and contact-edge models have identical inputs or guarantees.
- Long full-resolution research videos and every expensive fitting pipeline
  were not regenerated. Existing evidence and fixtures are preserved.
- The repositories retain historical objects containing the old combined tree;
  this is a working-tree/package separation, not a history-size reduction.
