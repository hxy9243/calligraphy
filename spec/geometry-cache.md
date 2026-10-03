# Geometry snapshots, database storage and engine identity

The font renderer continues to load local JSON banks from
`CALLIGRAPHY_STYLE_DIR` (default `~/.local/share/calligraphy/styles`). The Kai
example loads committed fixtures when launched. No fitting occurs during frame
replay. A JSON snapshot can be tracked in Git; the SQLite file is local runtime
state and is ignored by Git.

## SQLite and portable JSON

`calligraphy.artifact_cache.ArtifactCache` stores complete JSON geometry artifacts
without altering their schema or provenance. It supports font banks, Kai replay
bundles and study banks. Each version is identified by a SHA-256 of canonical JSON,
including its metadata. Multiple revisions coexist; callers must select a content
ID when a name has multiple versions. Imports do not replace newer local work.

```sh
.venv/bin/python -m calligraphy.artifact_cache --db work/geometry.db import spring-dawn examples/kai-stroke-ir/fixtures/chun-xiao-programs.json
.venv/bin/python -m calligraphy.artifact_cache --db work/geometry.db list
.venv/bin/python -m calligraphy.artifact_cache --db work/geometry.db export spring-dawn work/snapshot.json
# Use --content-id HASH on export when more than one version exists.
```

Applications can load Git snapshots into the database on startup:

```python
from calligraphy.artifact_cache import ArtifactCache
cache = ArtifactCache('work/geometry.db', snapshots=[
    ('spring-dawn', 'examples/kai-stroke-ir/fixtures/chun-xiao-programs.json'),
])
bundle = cache.get('spring-dawn')
```

Startup loading is explicit, idempotent and additive. The legacy font registry and frozen replay demo do
not automatically switch to SQLite. Generic Kai generation now uses SQLite by
default; see [generic Kai generation](kai-generation.md). Exported JSON retains their input formats:
use an exported Kai bundle with the demo's `--bundle`, or place an exported font
bank in the style registry. Import validates finite JSON and the schema field;
it is a storage layer, not a geometry validator. Renderer loaders retain their
own validation. Database reads verify the snapshot checksum.

Font-bank exports contain managed font paths and license text. Moving a bank to
another machine requires installing the same font and updating its path while
preserving its checksum before extending it. Do not commit a font or font-derived
snapshot without checking its redistribution license.

## Producer identity

New font fits store `glyph_metadata[character]`. New Kai contact fits record
`report.engine`. Replay output manifests separately record `replayEngine`, which
identifies playback code, not the original fitter.

Each record contains:

- `engine_type`: `font-contact`, `kai-fitted`, or `kai-replay`.
- `engine_version`: explicit implementation version (`font-contact-v1`,
  `kai-fitted-v1`, or the replay IR version).
- `engine_code_commit`: full Git revision when running from a source checkout;
  null when unavailable, including installed wheels without Git provenance.
- `engine_code_dirty`: whether engine sources/package configuration have local changes.
- `engine_source_sha256`: a hash of all Python engine sources, including local changes.
- `package_version` and UTC `prepared_at`.

Engine versions are maintained explicitly when algorithms change. The code hash
also distinguishes edits made without a version bump. In legacy font banks and imported snapshots, this metadata does not
trigger automatic refitting. Generic Kai includes source and guide hashes in its
cache key, so changed source or guides automatically prepare a new revision.
Old banks and frozen fixtures remain readable and are not retroactively stamped
with current producer metadata. Missing metadata means unknown producer identity.
A Kai caller assembling IR should preserve the fitter's `report.engine` in its
program provenance; validation does not require historical fixtures to contain it.

The Kai writing demo also supports actual startup import/read through SQLite:

```sh
.venv/bin/python examples/kai-stroke-ir/render.py frame --cache-db examples/kai-stroke-ir/work/geometry.db
```

It validates the selected `--bundle`, stores it under `kai-writing-scene`, and
loads the exact content ID back for replay. Repeated startup reuses that database
row. Other versions remain available for JSON export. The gallery still uses its
JSON bank directly.
