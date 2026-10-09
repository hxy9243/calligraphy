# Parallel editor-preview validation — 2026-10-09

Base: `09712c636da71c67280cbbd17a8dea34fb54549e`. The changed engine's source
SHA-256 is `c1cffaf21d6bdcbc94ebc4fee5b3ec62e457372b829e473f0a59b9358199cc55`.
This is a scheduling-only change: cached geometry, glyph order, stroke order,
partial-frame replay and final composition retain their existing contracts.

## Measurement

Linux x86_64 cloud runner, AMD EPYC 9V74, Python 3.12.14, nine affinity-visible
CPUs, two fitting processes maximum. Cgroup filesystem was not exposed on this
runner; the quota/memory guards were separately exercised with fixture tests.
Runtime dependencies installed from `deploy/requirements-studio.lock` include
OpenCV 4.14.0, NumPy 2.5.3, Pillow 12.3.0 and SciPy 1.18.1. Native math threads
were limited to one. These are local measurements, not Railway measurements.

`scripts/benchmark-preview.py` measures complete editor subprocess startup,
geometry preparation, rasterization and PNG encoding at 480×640. Each worker
setting gets its own empty geometry database; the next subprocess reuses that
database. This deliberately measures warm *geometry*, bypassing the existing
whole-preview LRU. No glyph downloads were needed. Serial and parallel settings
must produce byte-identical PNGs in every measured run.

| Text | Runs per setting | Serial cold | Bounded cold | Serial / bounded warm |
| --- | ---: | ---: | ---: | ---: |
| 春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少 | 3, medians | 24.621 s | 17.362 s | 1.468 / 1.468 s |
| 春眠不覺曉，處處聞啼鳥 | 1 | 18.586 s | 15.919 s | 1.318 / 1.419 s |
| 明月松间照 | 1 | 6.387 s | 6.921 s | 0.968 / 1.018 s |

The 20-character cold preview improved **29.5%**. Its serial samples were
25.2859, 24.6208, 23.3548 s; bounded samples were 18.3668, 17.3622, 17.2648 s.
PNG SHA-256: `34a40039fd03c9241d508577e51534fbbb0d43b956963b333dfbfa039e362977`.
The traditional ten-character cold case improved 14.4% in a single trial.

The five-character case takes the **same serial fitting path** under both
settings, because its 40 uncached strokes are below the 64-stroke threshold;
there is no claimed speedup for it. Exploratory runs without that threshold
showed process startup outweighing gains for short text. Two-thread fitting
showed no meaningful improvement, motivating process isolation rather than
wrapping the CPU work in threads. Warm geometry never starts a process pool.

Source-font previews continue using Pillow. An exploratory five-character
Ma Shan Zheng profile measured about 0.95 s on first import and 0.03 s on a warm
in-process render; roughly 0.91 s of the first run was imports. Parallel fitting
does not address that import cost and does not change source-font rasterization.

Reproduce:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/benchmark-preview.py
.venv/bin/python scripts/benchmark-preview.py --repeats 1 --text '春眠不覺曉，處處聞啼鳥'
.venv/bin/python scripts/benchmark-preview.py --repeats 1 --text '明月松间照'
```

## Regression results

- Full Python suite: 179 tests passed. After adding the explicit editor deadline
  regression, all nine final parallel-preview tests passed separately.
- JavaScript suite: 91 tests passed, including real PNG/video smoke tests.
- Downstream lab at `a66311dba31e684787a2863e5299dbd38266f76d`:
  `experiments/kai-stroke-ir/test_fit.py` and `test_contact_fit.py`, 15 passed.
- `pip check`, Python compilation and `git diff --check` passed.
- Independent review passed after fixing nested/inherited cgroup detection and
  making the affinity-budget test portable to platforms without that API.

The sandbox needs writable `CALLIGRAPHY_KAI_CACHE` and
`CALLIGRAPHY_CONTACT_CACHE` paths; test-only dependencies include IPython,
httpx and pytest. Initial runs without those test prerequisites failed and were
rerun successfully. No application dependency or lockfile changes were required.

The new tests cover bounded outstanding tasks, process-worker maximum, ordering,
duplicate reuse, warm/small/one-worker fallback, fit-error propagation and queued
cancellation, parent process-group timeout cleanup, inherited CPU/memory limits,
and actual spawned-process pixel equality for partial/final/backwards-seek frames.

No Railway configuration or deployment was changed as part of this validation.
The pre-existing Railway status on the base revision was failed; a source push
alone does not establish that a live demo is updated or healthy.
