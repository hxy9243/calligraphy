# Shared font-contact residue cleanup

The shared preparation pipeline now applies conservative automatic attached-ink
cleanup to every registered font's inferred contacts. It retains the source
font bank and completed glyph alpha, and rejects proposals that introduce new
detached ink in sampled partial frames. The implementation follows the Shou
Jin investigation and cross-font study described below.

## Root cause and evidence

Guide registration and broad ribbon overlap can assign a neighboring branch to
the wrong stroke. It is already present before brush replay. A finished-glyph
shape score hides the error because the ink belongs somewhere in the character;
the defect is most visible in isolated strokes and partial drawing frames.

Two cases require different remedies:

- Detached duplicates: a minor separate component can be removed if another
  stroke's primary component already covers at least 99.5% of it. Primary
  pieces, full dots and unique ink remain protected.
- Attached branches: trim the donor's derived envelope and reassign its original
  alpha to a supported neighboring stroke. Refitting the receiving stroke or
  recovered patch was rejected because it distorted otherwise correct ink.

The original 24-character Shou Jin study found detached duplicates in 中 and 瘦.
Three reviewed attached corrections then addressed 明、月、清. The broad left
entry point in 清 was retained; the smaller central spur was reassigned.

A subsequent study covered 20 complex glyph/font cases across seven font
registrations. A character-independent detector proposed 24 distinct edits.
All preserved completed alpha, but four revealed detached ink too early.
Twenty passed the sampled mechanical checks. This established the need for a
motion gate rather than unconditional automatic trimming.

## Implementation

- `stroke_crossings.py` implements conservative covered-satellite removal for
  inferred contacts, followed by the existing crossing geometry safeguards.
- `contact_ownership.py` supplies original-alpha transfer and exact-fit reviewed
  Shou Jin corrections. Review guards include font and source/prepared geometry
  hashes. Source rails, metadata, segment timing and stroke count are preserved.
- `automatic_contact_ownership.py` detects short interior rail excursions using
  local-width scaling, terminal/turn protection, neighboring ink support and a
  recipient confidence margin. There is no font-name allowlist.
- `contact_preparation.py` runs reviewed corrections first, then the automatic
  pass, and caches the result with the complete engine source hash.
- `contact_stroke.py` replays sparse derived alpha clips and timed transfers in
  the existing shared still/video renderer.

Automatic candidates are deterministic and bounded to 16 per glyph. A stroke
can participate in at most one correction in the pass; existing reviewed
ownership is reserved. The transfer helper rejects overwrites explicitly.
Each proposal is tested against the accumulated result, including previously
accepted edits and every intervening scheduled stroke. A failed proposal rolls
back only itself. Exact completed alpha, monotonic replay and sampled partial
connectivity are separate gates.

Transferred ink begins when the nearest recipient ink reaches solid coverage,
not merely its faint antialias fringe. Connectivity is checked at 65 progress
values and rejects new detached components of at least four binary pixels.
These are mechanical safeguards, not proof of historical brush movement.

## Scope

All registered fonts in `auto`/`contact` mode use the pass, including future
registrations. Authored built-in collections and generic Kai/yan Stroke IR
retain their existing preparation; direct static font output and explicit
`font_layers` mode do not need this inferred-contact ownership correction.
Other small or ambiguous residue may remain. Multiple proposals sharing a
stroke are deliberately deferred instead of combining unverified boundaries.

## Reproduction and validation

The private `calligraphy-lab` repository owns the study under
`experiments/shoujin-residue/`. It imports the installed engine; the engine does
not import lab code. Fonts, private source geometry, environments, caches and
rendered outputs are not included in the commit.

`shared_pipeline_audit.py` exercises the real preparation/cache pipeline on
23 cases across seven fonts, including the three original reviewed glyphs.
It checks combined edits, exact final alpha/RGB, cold/warm cache equality and
backward seeking through every stroke. Evidence and run metadata are kept in
its ignored `work/shared-pipeline/` directory. Earlier rejected experiments and
raw observations remain in the lab experiment.

Synthetic regressions cover automatic branch detection, any-font preparation,
source/metadata preservation, ambiguity rejection, terminal protection,
authored-input opt-out, disjoint combined corrections, overwrite protection,
early-island rejection, sparse replay and cache round-trips. The older detached
regression also remains in `test_stroke_crossings.py`.

Historical baseline: the first worktree run at `e54e325` had two export-warning
failures and one video-range failure. Main subsequently fixed the warning
expectations; this integration was updated to `3ce847c` before final testing.
Final validation: 292 engine tests ran on the integrated tree; 291 passed and
one failed (`test_range_request_streams_native_attachment`, HTTP 200 vs 206).
That failure was reproduced independently on unchanged main at `3ce847c` using
the same environment. All 13 ownership-focused tests and all 24 downstream lab
regressions pass.

The 23-case shared-pipeline audit passes exact final alpha/RGB, cold/warm cache
and backward-seek checks. It accepts 18 automatic edits in 13 cases, rejects
four proposals for early detached ink and skips five overlapping corrections.
The three original reviewed Shou Jin corrections remain applied and preserved.
A final combined-result comparison was visually inspected. The full suite is
not green because of the independently reproduced existing video-range failure.
No production deployment or main-branch merge is implied by this branch.

Before commit, the branch was fast-forwarded to main `4e637dd`; that final
upstream update changes only frontend code, its tests and UI documentation.
The tested Python implementation and Python test files are unchanged.
