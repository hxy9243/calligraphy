# Pinned brush-fitting experiments

The reference-fitting studies associated with this Kai stroke IR worktree are
committed in the separate `calligraphy-lab` repository, following the ownership
boundary described in `architecture.md` and `assets-and-validation.md`.

## Revisions

- Laboratory snapshot: `a8d2ca7fa831dcdb5716280d7349b3ca0b08baa8`.
- Preceding anchor/poem study commit: `9407c29`.
- Engine runtime baseline used by the studies:
  `026da673b40934bdc1fad749ae5c5ee754a94241` on `feature/kai-stroke-ir`.

This checkpoint adds a reference to the laboratory evidence; it does not promote
the optimizer or change the engine's supported runtime. The studies use the
installed engine's contact deposition and retain source stroke order. Other
uncommitted cleanup/regularization work in this worktree is not part of this
checkpoint.

## Laboratory entry points

- `experiments/anchor-morph/`: shared anchor deformation, tuning, and poem study.
- `experiments/brush-fit/`: independent stroke initialization and constrained
  contact sweeps, with isolated-stroke and incremental replay inspection.
- `experiments/brush-fit/expansion/`: three-font comparison covering 18 characters
  per font; 42 new automatic fits and 12 earlier pilot cases shown as context.
- `experiments/brush-fit/expansion/smooth.html`: separate uniform body-smoothing
  ablation; not a blanket replacement for the automatic results.

For the 42 new cases, mean deposited-mask IoU is 96.93% for Chill QiuHong Kai,
93.68% for YouRan XiaoKai, and 93.13% for Long Cang. Thirty-nine reach 90% IoU;
Long Cang 鸟、林、雨 remain failures. Independent render/replay verification covers
261 new strokes. Visual audits additionally identify wrong ink ownership,
hidden protrusions and cumulative zigzags that local numerical gates can miss.
These are reference-specific fits, not learned unseen-character style transfer
or calibrated brush physics.

## Validation and artifact boundary

Before checkpointing, all nine anchor/style regression tests and all three
independent-stroke regression tests passed. The measured runs retain their own
configuration, input/model hashes, runtime provenance and verification reports
in the laboratory snapshot.

Runners, viewers, protocols, metadata and metric evidence are committed. Generated
model caches, reference/font assets and rendered media remain in ignored local
work directories, as documented by `experiments/brush-fit/README.md` in the lab.
They are preserved locally; a fresh checkout must regenerate those prerequisites
before using the interactive replay pages. No generated media or laboratory
runtime dependency is copied into this engine repository.
