# Promoted contact renderer

## Selection and evidence

The main repository packages the latest contact-strip style-transfer results
from lab revision `cc67163` (full revision and checksums are in the asset manifest).
The existing `ContactBrush` algorithm is unchanged. Prepared geometry is copied
byte for byte; fitting tools and reference images remain in the lab. These three
reference styles were generated artwork, not font glyphs or historical scans.
For Lishu, `contact-style-transfer/prompts.json` records an AI-generated reference
sheet inspired by the Cao Quan stele. The silhouette scores below therefore
measure reconstruction of that generated reference.

| CLI style | Recorded mean silhouette IoU | Minimum |
| --- | ---: | ---: |
| `yan-contact` | 0.973796 | 0.958728 |
| `liu` | 0.969878 | 0.952490 |
| `lishu` | 0.963646 | 0.933822 |

These scores measure completed silhouette reconstruction on the prepared glyphs,
not runtime performance, historical authenticity, unseen-text quality or correct
stroke motion. Yan has the highest mean on these saved results; contact strips
were the strongest supported reconstruction approach among the inspected lab
studies. Motion and some stroke decompositions are inferred.

Each bank contains 25 distinct traditional characters and 237 strokes:

```text
人有悲歡離合月陰晴圓缺此事古難全但願長久千里共嬋娟
```

Any ordering or repetition of these characters is supported. Simplified forms
are distinct. Missing glyphs fail explicitly; no template fallback occurs.
Wang Xizhi is not a supported contact style. `yan` remains the existing template
width preset; use `yan-contact` for the prepared Yan contact geometry.

## Pipeline and ownership

1. `scripts/render-text.mjs` parses CLI options and requests bank stroke counts.
2. `createTextPlan()` applies the shared text, punctuation, layout and timing
   policies using those actual counts.
3. `src/bridges/contact.mjs` passes the serializable plan over stdin to
   `python -m calligraphy.contact_renderer`. The npm root exports
   `describeContactStyle` and `renderContactStyle`; the browser text subpath stays
   independent of Python and subprocess APIs.
4. `ContactScene` validates the plan and snapshots its inputs. `ContactBrush`
   deposits paired-boundary strips in canonical 480 × 480 glyph space with the
   existing supersampling. Stroke coverage is max-composited.
5. Frames place glyph masks inside the planned cells with a 4% inset, using the
   lab's ink color, ivory paper and Lanczos scaling. Completed glyph patches are
   cached. Repeated placements have separate active painters. Backward seeking
   resets active paint state and replays deposition.
6. PNG and MP4 use the same `frame(time)` implementation. MP4 streams raw RGB
   frames to FFmpeg/H.264; the final sample is explicitly the completed scene,
   including at low frame rates. Video dimensions must be even.

The output uses the generic page layout and plain paper. Lab-specific decorative
backgrounds, captions and composition are not copied, so a whole-page render is
not a pixel-identical reproduction of the lab movie.

## Installation and use

From the repository root, after `npm ci`:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
npm run render:text -- --text '人有悲歡離合' --style lishu --output outputs/lishu.png
npm run render:text -- --text '人有悲歡離合' --style liu --output outputs/liu.mp4
npm run render:text -- --text '但願人長久' --style yan-contact --time 1 --output outputs/yan-partial.png
```

The bridge selects an explicit API `pythonPath`, then `CALLIGRAPHY_PYTHON`, then
`PYTHON`, then the repository `.venv/bin/python`, otherwise `python3`. Install the
Python package in the selected interpreter. FFmpeg is required for MP4. Contact
styles support PNG/MP4 only; `--fetch`, `--glyphs` and SVG output are rejected.

## Provenance and validation

`python/calligraphy/assets/contact/manifest.json` records each source path,
revision, SHA-256 checksum, coverage and recorded reconstruction score. The
loader verifies checksums. The accompanying Arphic license is packaged alongside
the banks. No runtime operation reads from the lab repository or the network.

`tests/python/test_contact_renderer.py` checks bank integrity, original deposition,
partial/final frames, backwards seeking, repeated glyphs, input isolation, invalid
plans, PNG export and real video encoding. `tests/contact.test.mjs` checks the
Node bridge, CLI selection and failures, including execution outside the repo.

Promotion validation recomputed all 75 prepared glyphs against the original lab
targets: every per-glyph IoU matched its saved metric within 1e-12. Existing
JavaScript frame regressions remain unchanged. This supports geometric fidelity;
it does not certify stylistic authenticity or inferred writing trajectories.

### Promotion checks (2026-09-26)

- Main JavaScript suite: 31 passed, no skips; working-tree Python suite: 26
  passed (including seven pre-existing notebook/animation tests outside this change).
- Clean committed-source package installed into a fresh virtual environment:
  all 19 committed Python tests passed. Isolated module discovery and a Node CLI
  PNG render from `/tmp` succeeded with the installed banks.
- Downstream lab brush-grammar regressions: five passed; lab checkout unchanged.
- Lishu and Yan contact PNGs were visually inspected. Liu MP4 was verified with
  FFprobe: 240 × 480, 15 frames, 3.75 seconds at 4 fps and speed 4.
- Original license text was copied verbatim, including its two trailing spaces;
  this is the only whitespace-check exception in the promoted files.

Generated smoke outputs and the full 75-glyph score comparison are local ignored
artifacts under `outputs/`, not package inputs. Existing notebook/animation work
was neither changed nor included in the promotion commit.

## Font-based expansion experiment

The lab's `experiments/lishu-font/` now supplies a reproducible starting point:
Wang Hanzong's HanWangLiSuMedium (王漢宗中隸書繁), version 1.3, downloaded
from the Wang fonts project archive with its GPL-2.0-or-later notice and checksums.
The font exposes 13,068 mapped CJK code points in the checked ranges. The first
19-character target set includes 18 characters outside the existing Lishu bank.

Font-derived silhouettes supply consistent final shapes, but not ordered brush
strokes. The lab still needs to register stroke guides, decompose overlaps, fit
contact strips, and validate partial and final frames before promoting these
characters. Keep the font-derived style separate from the generated-reference
`lishu` bank. No additional characters or font-based style are enabled in the main
CLI by this preparation experiment.
