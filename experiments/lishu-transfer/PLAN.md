# Clerical-script transfer experiment

Starting point: main `4e2a9722b0995da977faf8fde2a7d55316d5bbf7`.
Branch: `experiment/lishu-transfer`. Production code stays unchanged.

## Question

Can the approved overlap-preserving animation pipeline transfer from Kai-inspired
artwork to generated 隶书, while keeping the new artwork's ink and stroke ends?
This tests script transfer of the pipeline and image prompting, not learned
transfer of a historical calligrapher's identity.

## Fixed inputs and comparison

- Ten characters: 明月松間照清泉石上流, from the existing poem and stroke data.
- Source: existing Yan-inspired normalized glyphs, indices 10–19.
- Target A: reference-conditioned rewrite, retaining substantial ink weight.
- Target B: text-only generation requesting lighter, wider clerical forms.
- Control: the unchanged main pipeline on the Kai input and both targets.
- Adaptation: fit the template ink bounding box independently in x/y to the
  target before the same optical flow; retain the original overlap compositor,
  threshold, one-pixel support collar, and component filter.
- No manual masks, larger support dilation, nearest-stroke fill, or final reveal
  in either comparison. Save omitted ink visibly instead of hiding it.

## Evaluation decided before running

1. Inspect all ten target identities, isolation, broad forms, and flared endings.
2. Report per-character and aggregate retained ink and empty stroke layers.
3. Inspect colored ownership maps and intermediate stroke-boundary frames,
   especially 月, 間, 清, 泉 and the long final stroke in 上.
4. Render synchronized unchanged/adapted animations with static target reference.
5. Check monotonic reveals, finite supported exposure, and final-frame equivalence
   to retained masks; run existing overlap regression tests.

A useful provisional result retains at least 95% mean ink with no empty layers,
but retention is NOT stroke correctness. A visible wrong branch reveal prevents
claiming production readiness even if those numeric checks pass. Do not estimate
a population success probability from two generated sheets of the same text.

## Deliverables

Commit inputs, exact prompts, executable experiment, metrics, audit images,
comparison video and a report of failures and next steps. Keep the branch
separate from main for review.
