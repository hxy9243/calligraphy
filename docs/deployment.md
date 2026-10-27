# Calligraphy Railway demo

The demo frontend and Python API run in one Docker container and one Railway
replica. One persistent volume at `/data` holds SQLite job history, creation-rate
events, outputs, registered style banks and derived geometry caches. No separate
PostgreSQL or Redis service is required for this deployment.

## Artifacts and target

- `Dockerfile`: Python 3.12, FFmpeg, Cairo and the engine/studio installation.
- `.dockerignore` and `.railwayignore`: explicit runtime file allowlists; no local environments or research outputs.
- `deploy/requirements-studio.lock`: pinned Linux/Python 3.12 runtime dependencies.
- `deploy/start.sh`: one Uvicorn process, Railway's `PORT`, graceful shutdown.
- `deploy/check_storage.py`: with `CALLIGRAPHY_PERSISTENT_ROOT=/data`, refuses
  startup if SQLite or artwork paths escape that writable root. This guard checks
  path configuration, not whether the platform actually attached a durable volume.
- `deploy/check_fonts.py` and `deploy/font_assets.json`: verify SHA-256 for all
  source fonts; restore missing fonts from the private persistent volume.
- `deploy/prepare_samples.py`: pre-render 永 PNG thumbnails before startup;
  these generated images and private font inputs are not committed to GitHub.
- `.railway/railway.ts`: Railway's current IaC format; named partial owns only
  `calligraphy-demo` and its volume, leaving the other project service unmanaged.

Target project: `e793b673-52a2-4605-940f-a439e990cf26` (`charming-magic`).
Demo service: `calligraphy-demo`; environment: `production`; region: `us-west2`.

The CLI-created volume has a 50,000 MB capacity ceiling; this is not a claim of
current storage consumption. Do not shrink or replace it while deploying updates.
Back up the volume before destructive changes. A mounted volume plus SQLite
requires one replica; changing to multiple workers requires a separate design.

## Deploy

```sh
npm ci
railway link --project e793b673-52a2-4605-940f-a439e990cf26 --environment production --service calligraphy-demo
# Seed private font inputs before deploying a fresh Railway service.
tar -C data/fonts -czf /tmp/calligraphy-font-assets.tar.gz .
railway service files upload /tmp/calligraphy-font-assets.tar.gz /data/calligraphy-font-assets.tar.gz
railway ssh -- mkdir -p /data/font-sources
railway ssh -- tar -xzf /data/calligraphy-font-assets.tar.gz -C /data/font-sources
railway config plan
railway config apply --yes
railway up --service calligraphy-demo --environment production --detach
railway deployment list --service calligraphy-demo --json
railway logs --service calligraphy-demo --lines 100
railway domain --service calligraphy-demo --port 8080
```

Inspect the plan before applying: it should affect only the demo service/volume.
Uploading does not confirm successful deployment. Verify deployment status and
`GET /health`, then exercise preview, render, playback, download and history.
The original `calligraphy` service is outside this manifest's named partial.

## Font assets

The evaluation image includes all 59 available local source fonts, including
four additional locally registered fonts, plus the generic Kai/Yan renderers.
`CALLIGRAPHY_DEMO_ALL_FONTS=1` explicitly enables the full evaluation catalog,
including fonts with noncommercial/restricted notices. It overrides the ordinary
public allowlist and restricted-style guard; without this flag the guard remains.
Preserve matching font notices and embedded metadata under `data/licenses`.
An embedded notice or catalog license designation is not a grant of new rights.

Source fonts remain private server inputs; no font directory is mounted in the
HTTP app. Pre-rendered PNG 永 samples support every font card, picker row and
selected-font badge, including Kai/Yan. `POST /api/editor-preview` returns
a raster image after editing pauses, using the source font for catalog styles
and the scene renderer for built-in Kai/Yan. Font previews show actual glyphs;
the inferred brush renderer used for exports can differ in texture and layout.
Previews are bounded to 640 pixels per side, 256 characters, one concurrent
preview process and a 120-second deadline. A 32-entry cache avoids repeated work.
Automatic editor previews do not create jobs or spend the export allowance.
Rendering status sits outside the artwork viewport. A separate missing-character
alert names missing glyphs and blocks exports until the text/font changes.
First visits use Traditional Chinese interface text, initial text and presets.
No font-upload or direct font-download endpoint exists. Font-derived motion is
inferred. The header links to the public GitHub repository so visitors can star it.

The combined font/code archive exceeded Railway's HTTP upload limit (413 at
461 MB). `.railwayignore` therefore includes only three bootstrap font binaries;
the rest are uploaded using Railway's authenticated file transfer to
`/data/font-sources`. Startup restores and verifies all 59 fonts before accepting
requests. Include this directory in persistent-volume backups. Local Docker
builds include all source fonts directly and also pass the same hash check.

Four additional evaluation font binaries are deliberately omitted from public
GitHub: AA Shoujin, Chiron Go Round TC, HanWang Kan Da Yan and the local Qiji font.
Provision them alongside the catalog fonts on the private volume. A source-only
checkout marks absent font inputs as unavailable. The full Docker/demo startup
requires all source hashes in `deploy/font_assets.json` and fails if inputs are
missing or differ, instead of publishing a partial catalog.

The demo has a private intended audience but no authentication gate. Anyone with
the Railway URL can open it. Do not describe the URL as access controlled.

## Limits, failure and retention

Three new still/video creations per rolling minute per anonymous browser session.
Repeated submissions of an identical active video reuse that job. Deleting a
history record does not restore the budget. HTTP 429 includes `Retry-After`.
Clearing cookies creates a new identity; the limit is not account or IP based.
A separate atomic 30-work storage limit includes ordinary and shared works plus
in-flight saves. Failed jobs do not consume storage slots. Existing over-limit
histories are preserved; new saves are rejected until a slot is freed.

Ten active jobs globally, one compute slot, dimensions 64–1280 pixels per side,
at most 120 output seconds and 3000 frames. A deployment job gets a 600-second
wall-clock deadline including font preparation. The process group is killed on
deadline or service shutdown, including FFmpeg. Interrupted jobs are failed with
a retry message on restart; queued jobs survive. Automatic retries are disabled.

Unshared outputs and terminal history expire after 60 days by default, configurable with
`CALLIGRAPHY_RETENTION_SECONDS` (default: `5184000`). Cleanup also removes expired
output files whose history was deleted. Caches are persistent and do not share
the output TTL. Cookies are Secure, HttpOnly and SameSite=Lax; browser mutation
requests must be same-origin. Clearing browser data loses access to old jobs.

## Verify locally

```sh
pip install -e '.[studio]'
python -m unittest discover -s tests/python -p 'test_*.py'
npm test
docker build -t calligraphy-demo:local .
docker volume create calligraphy-demo-local
docker run --rm -p 127.0.0.1:8088:8080 \
  -e CALLIGRAPHY_SECURE_COOKIES=0 \
  -v calligraphy-demo-local:/data calligraphy-demo:local
```

Disabling Secure cookies is only for local HTTP testing. Keep them enabled on
Railway HTTPS. Test two-session isolation, font URLs returning 404, rate-limit
responses, actual PNG and H.264 exports, reload during work and restart recovery.

## Google Analytics

Set `GOOGLE_ANALYTICS_ID` (a GA4 `G-...` measurement ID) in the Railway
`calligraphy-demo` service's production variables. It is read at runtime through
`GET /api/analytics-config`; no frontend rebuild or hardcoded ID is needed.
An unset or invalid ID disables analytics. Restart/deploy after changing the
environment variable. Keep the ID in Railway rather than the IaC manifest.

The workbench loads the asynchronous Google tag and initializes pageview
measurement. Query strings and fragments are omitted from its configured page
URL and referrer. It does not send custom artwork, text or job events. The
capability-link watch/export pages do not load analytics. A blocked Google tag
or failed configuration request does not interrupt the workbench.

## Public URL

Artwork QR seals and generated job share URLs default to
`https://calligraphy.kevinhu.me`. `CALLIGRAPHY_STAMP_URL` can override it for
another deployment.

## Release validation — 2026-10-09

Original public demo: https://calligraphy-demo-production.up.railway.app

Railway deployment: `1f7640e2-e5f8-4197-960a-aedad2442885`, uploaded locally
to service `8d2735fa-99b2-4d60-9509-ec52b8f28037`. Railway reported SUCCESS,
`/health` returned 200, and the IaC plan had no pending changes. This service is
not connected to GitHub autodeploys.

Validation included 167 Python tests and 82 JavaScript tests; a fresh Docker build
and container execution; real PNG exports and a one-character H.264 MP4 at
240×320, 2 fps, speed 4; HTTP 429 for a fourth creation in one minute, including
`Retry-After`; font paths returning 404; two-session isolation; HTTPS cookie
flags; same-origin POST; and HTTP 206 video byte-range streaming.

A local container restart during an actual active render failed that job with a
retry message and retained a previous completed MP4. A Railway restart retained
the cloud job history and downloadable/streamable video. These small smoke
exports are functional evidence, not a throughput or long-poem benchmark.

Visual desktop/mobile verification remains unverified: the computer-use browser
was denied because its admin-enforced browser policy could not be verified. No
alternate browser-control method was used.

## Full-font evaluation update — 2026-10-09

Railway deployment `8b72685d-d0f1-4ad7-a55b-b4c3530bb8ec` reported SUCCESS.
All 59 font files were transferred through authenticated Railway file transfer
to the existing volume and verified with SHA-256 before startup. The application
archive contains three bootstrap fonts plus 61 precomputed 永 PNG samples.
The final IaC plan has zero changes, and the deployed frontend file hashes match
the tested local source exactly. No source changes were pushed to GitHub.

Live validation covered the 59-font catalog and 61 styles; every raster sample;
AA Shoujin, ShuTiFang, TW Sung and Kai editor previews; authoritative missing-glyph
HTTP 422; real AA/ShuTiFang PNG exports and an AA H.264 MP4; a fourth export
returning 429; private font paths returning 404; same-origin previews and secure
cookies; no automatic-preview history entries; and two-session output isolation.
A small Docker image restored all fonts from mounted private storage and passed
the same startup hash validation. Temporary transfer files were removed from
the volume after installation.

Final checks: 170 Python tests and 85 JavaScript tests passed, including backend-only picker
samples, stale-response rejection, status placement outside the artwork, exact
missing-character warnings (including stale-error rejection), blocked exports, Traditional defaults and the Star
link. Browser visual verification remains unavailable for the policy reason
recorded above.

## Creation and browser notices update — 2026-10-09

Railway deployment `0f6596e6-266f-47f6-9305-cdf1bb301ae2` reported SUCCESS.
Live health returned 200, all 61 styles remained available, and sampled backend
previews returned PNGs. Private font paths returned 404. Deployed frontend and
sample-generator hashes match the tested local files; the IaC plan has no changes.

Accepted generation requests open a separate confirmation popup and move to
history after three seconds. Visitors can view history immediately or stay on
the creation page; rejected requests never acknowledge or redirect. The GitHub
Star link is the final header control on the right. A MicroMessenger advisory
offers opening in Safari/Chrome and copying the URL, with a manual-copy fallback.
It appears once per tab after dismissal and leaves creation/download available.

Font samples are now generated at container startup from verified private
inputs. Newly generated images and the four private font inputs are excluded
from the public source commit. Source-only checkouts mark absent inputs as
unavailable. A fresh small container restored all 59 source fonts, prepared
61 thumbnails and returned 61 styles; font-download paths returned 404.

Checks: 89 JavaScript tests passed, including popup timing, failed submissions,
dismissal, WeChat detection/copy fallback and header order. The full Python
suite passed 170 tests; the release-specific suite then passed all 14 tests,
including the additional missing-private-input regression. Actual phone and
visual browser verification remains unavailable as described above.


## Retention rollout and durability checklist

The 60-day policy requires `CALLIGRAPHY_RETENTION_SECONDS=5184000` (or unset).
The IaC manifest previously forced **86400 seconds**, overriding the Python
default; inspect the actual production variable before applying this release.
Code/config edits alone do not update a deployed service.

- Review the pre-existing QR-token setting `CALLIGRAPHY_SHARE_SECRET`: the source
  fallback is public, so it is not a production secret. Provision a strong stable
  value through secret management before relying on QR capability secrecy; never
  print it in logs. Changing it affects initial links for already-rendered QR
  stamps, so coordinate that change separately rather than silently rotating it.
- Back up the existing `/data` volume, including SQLite and outputs, before rollout.
  Use SQLite's online backup API or stop writes for a consistent database backup;
  keep the matching artifact tree. Do not copy only a live SQLite main file and
  discard its WAL.
- Verify the existing volume remains mounted at `/data`; do not recreate it.
  `DATABASE_URL=sqlite:////data/calligraphy.db` and
  `CALLIGRAPHY_OUTPUT_DIR=/data/outputs` must both resolve inside that volume.
  Container-local disk alone does not survive replacement/redeployment.
- The additive sharing migration preserves existing records and upgrades live
  legacy share leases to non-expiring shares. Expired/revoked links are not revived.
  Existing histories above 30 are not trimmed. No retroactive quota eviction runs.
  The migration conservatively marks old jobs as previously issued, because the
  old code did not persist revoked-link history. Existing live links retain their
  hashes and work; a never-shared pre-upgrade artwork's printed QR may not match
  its first newly created link. Use the owner's Share dialog link in that case.
- Retention cleanup remains destructive for eligible unshared records/artifacts.
  Before enabling a new build against production, inventory expired works and
  orphan files, review the count/age with the owner, and obtain approval for any
  destructive cleanup. A backup is not permission to delete existing data.
- Do not roll old code directly onto the migrated schema: its positional
  three-column share INSERT is incompatible with the added permanence column.
  Use a compatible rollback build, or restore the coordinated pre-upgrade
  database/artifact backup with explicit approval (restoring can discard new work).
- Verify an ordinary work and shared work (including file checksum), restart the
  service with the same volume, and verify owner history, output download and
  shared-link playback again. Local persistence tests prove filesystem behavior,
  not that Railway has the expected mount or backup policy.
- Shared retention means no automatic expiration, not protection against explicit
  deletion, share revocation, disk loss or storage-provider failure. Keep backups
  and monitor volume capacity. Cookie quotas are bypassable by clearing cookies;
  the existing rate/global queue limits remain in place.

No object store or additional paid service is required for the existing
single-replica volume-backed deployment. Scaling beyond one replica needs a new
storage/queue design rather than mounting independent ephemeral disks.


The 30-work limit is a count of owned active/successful records, not a disk-byte
ceiling. Explicit deletion still leaves orphan output files for ordinary TTL
cleanup, and failed renders may leave partial artifacts for that same cleanup.
Repeated save/delete or repeated failures can therefore consume temporary disk
space; the existing creation rate limit and disk monitoring remain necessary.
Quota-rejected requests never execute a renderer or create an output artifact.

### Staged release procedure (requires deployment approval)

1. Review the feature-branch diff and local regression results. Publishing this
   branch or a draft PR is not authorization to merge, deploy or change live data.
2. Read-only preflight: verify the production service's source branch, single
   replica, existing `/data` mount and nonsecret path/TTL overrides. Confirm no PR
   environment will deploy this branch. Record the currently deployed image/revision.
3. Arrange a maintenance window before stopping writes. Confirm a supported
   provider volume-backup method, its backup identifier/status and restoration
   procedure. If using a manual backup, quiesce both API writes and the worker,
   then snapshot the database and artifact tree together; do not rely on a raw
   copy of a live SQLite file. These state changes require separate approval.
4. Restore the backup into an isolated local/staging directory. Inventory rows,
   active shares, artifact paths/checksums, ordinary works already past 60 days,
   and orphan outputs. Run the migration against that **copy**, then compare row
   counts, old active share hashes, ownership and artifact checksums. Verify an
   existing live link and fresh-process ordinary/shared downloads. Keep production
   untouched and review the inventory before authorizing cleanup.
5. With explicit deployment/cleanup approval, retain the same production volume,
   set the nonsecret paths and 5184000-second retention, and deploy the approved
   exact commit. The worker runs retention cleanup after startup, so do not treat
   deployment as a read-only migration trial. Never recreate the volume.
6. Verify health, owner isolation, 30-slot rejection, ordinary/shared access and
   artifact checksums. Restart using the same volume and verify them again. If a
   check fails, stop new writes and use a compatible rollback plan; never blindly
   restore an old database over work created after the backup.

No production backup, maintenance window, deployment, cleanup, merge or rollback
has been executed by preparing this change.

Read-only rollout-preparation observation (2026-10-27): the existing production
`/data` volume and single replica were verified, but existing backup status and
schedules remain **unknown**. Current Railway MCP does not expose backup reads,
and the available browser is not authenticated. No backup was created or claimed.
Verify a whole-volume `/data` snapshot or a consistent SQLite/WAL plus artifact
backup using an authorized operator session before approving migration. Do not
interpret unavailable backup visibility as proof that no backups exist.
