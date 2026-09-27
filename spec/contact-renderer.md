# Promoted contact renderer

## Selection and evidence

The main repository packages the latest contact-strip style-transfer results
from lab revision `cc67163` (full revision and checksums are in the asset manifest).
The existing `ContactBrush` algorithm is unchanged. Prepared geometry is copied
byte for byte; fitting tools and reference images remain in the lab.

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
