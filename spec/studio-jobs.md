# Studio render queue and job history

After a render submission is accepted, a separate confirmation popup acknowledges
the queued work and redirects to history after 3000 ms. Users can open history
immediately or dismiss the dialog to keep editing; dismissal and Escape cancel
the redirect. Failed submissions never acknowledge success or navigate.
The confirmation never occupies the artwork preview.

This describes the implemented local SQLite-backed studio in `backend/` and
`frontend/`. The single-instance demo deployment is documented in [deployment](../docs/deployment.md).
The broader multi-worker service remains in [the MVP plan](../docs/mvp-plan.md).

## Submission and request identity

`POST /api/renders` validates text and output parameters, resolves style aliases,
and returns HTTP 202 with a `job_id` and the job's current `status`. It only
submits work; video rendering runs in the worker.

Within the same existing `calligraphy_session` browser session, an identical
active render is reused rather than creating another job. Identity includes the
exact submitted text, canonical style, and the entire validated parameter mapping
including frame rate, speed, spacing and layout direction. JSON key order and
equivalent numeric representations do not create different identities. Known
render defaults are filled before comparison, including the legacy vertical-rl
direction for older jobs that omitted it. Unknown parameter keys are preserved
in the identity rather than ignored. Changing any output parameter creates a
separate render. Distinct sessions never merge jobs or gain access to each other's
status, history or outputs. Concurrent first-ever requests without an established
session cookie are not assumed to be the same visitor.

The active states are `queued`, `rendering`, and the compatible `running` state.
A repeated POST returns that existing job's ID and status, which may already be
`rendering` rather than `queued`. Failed and successful jobs are excluded from
deduplication: submitting again after failure retries as a new job, and submitting
again after success intentionally produces a new render. This is active-work
coalescing, not a global output cache.

## Database and worker ownership

`Database.enqueue_render()` holds a SQLite `BEGIN IMMEDIATE` transaction across
the active-job lookup and insertion. The decision is serialized across separate
Database objects, connections, API instances and processes sharing the database;
a Python instance lock alone does not provide that guarantee. Parameter comparison
also reads older, non-canonically ordered JSON records without a schema migration.

`Database.claim_next_job()` takes the same database-level write reservation before
selecting the oldest queued render. It updates that row to `rendering`, verifies
that exactly one row was updated, and returns only the claimed job. Two concurrent
workers cannot both win a claim for the same queued row. Work is executed after
the claim transaction commits, so expensive rendering holds no queue transaction.

Still previews remain synchronous. `POST /api/previews` inserts its preview job
as `rendering` before directly executing it; it never temporarily queues the job.
The background claim also filters to `job_type = 'render'`, so even legacy queued
preview rows are ineligible for background execution. Worker completion records
`succeeded` or `failed` on the owning job.

The demo holds an exclusive file lease for the database's worker. A second
instance refuses startup before touching active jobs. Startup marks interrupted
`rendering`/`running` jobs failed with an explicit retry message; queued jobs remain
queued. There are no automatic retries. Deployment must run one API process and
one replica with the persistent SQLite volume.

Previews and videos share one compute slot. Previews wait at most five seconds
for that slot before failing with a retry message. In deployment, each admitted
job runs in its own process group with a 600-second wall-clock deadline. Timeout
and shutdown kill the renderer and encoder together. A failed process is recorded
as a failed job. The worker catches queue errors and keeps polling.

Both creation endpoints share an atomic sliding-window limit of three new jobs
per browser session in 60 seconds. Events persist in SQLite independently of job
history, so deletion and restarts do not reset the budget. Identical active video
submissions reuse their job without consuming another creation. Rejected requests
return HTTP 429 with `Retry-After`; invalid requests and full-queue rejections do
not consume budget. The global active-job ceiling defaults to ten. Without
accounts, clearing cookies creates a new identity; this is not an IP abuse limit.

Canvas dimensions are bounded to 64–1280 pixels per side, with even video sizes.
After preparation, videos above 120 seconds or 3000 frames are rejected before
encoding. Ordinary terminal history and output files expire after 24 hours (or
the configured retention); an explicitly shared video receives the 72-hour
retention lease described below. Cleanup also removes expired files whose
history was previously deleted.

## Browser behavior

Clicking Render submits immediately. Only the HTTP submission disables the Render
button; it becomes available again as soon as the request succeeds or fails. The
editor and preview controls remain usable while queued work runs. Validation and
submission errors can appear by the form because no accepted job exists yet.

After acceptance the job list refreshes. Each job card displays its own queued,
rendering/running percentage, completed or failed status. Failed cards contain
the associated error; completed video cards offer Play, Download and Share. Render
progress, completion and failure never use the shared inline form status. Job
completion does not open the export panel, start video playback, or change the
current editor contents; playback is an explicit card action.

One self-scheduled job-list poll tracks all active cards, including jobs restored
on page load. Known active jobs keep polling across transient network errors and
past three minutes; a browser-side timeout must not pretend the server job has
failed. Polling stops after a successful refresh sees no active jobs. An older
response cannot overwrite a newer submission's refresh, and repeated clicks do
not create extra poll loops or duplicate cards for the same server job ID.

## Regression checks

- `tests/python/test_render_queue.py`: concurrent API submissions, independent
  Database instances, single-winner claims, render-only FIFO, synchronous preview
  ownership, alias/default/parameter identity, session separation, and new work
  after both failure and success
- `tests/frontend-queue.test.mjs`: repeated submissions, restored-job polling,
  queued/running/completed/failed cards, network recovery, stale list responses,
  form usability, and completion without editor/media interruption

## History deletion

Each history card offers Delete and a confirmation dialog with Cancel. Active
jobs cannot be deleted; the button becomes available after success or failure.
`DELETE /api/jobs/{job_id}` atomically verifies session ownership and terminal
status before deleting the SQLite history row. It returns 204 on success, 404
for missing or other-session jobs, and 409 for active jobs. Deleted jobs no longer
appear in history or provide status/download access. Output files remain on disk
until the ordinary retention cleanup; deleting a shared video also ends its
extended retention lease. The browser reports
errors in the confirmation dialog and permits retry, refreshes counts after
success, and rejects list responses captured before deletion.

## Standalone video sharing

Completed video cards and their detail viewer offer Share. Opening the sharing
dialog alone does not publish a capability: the owner explicitly creates a link
after seeing that anyone holding it can watch and download this one video.
The dialog offers copying, a selectable-link fallback and revocation. Before
creation it explains the 72-hour lifetime and single-video access granted to
anyone holding the link. Creation and both clipboard/manual-copy feedback show
the actual expiry date/time and repeat that privacy notice.

`POST /api/jobs/{job_id}/share-link` requires the owning browser session and an
existing, completed, non-symlink MP4. It returns `/watch.html#job_id.token` and an
`expires_at` Unix timestamp. The bearer has 256 bits of entropy. SQLite's separate
`video_shares` table stores only the SHA-256 digest and expiry. A new share link
replaces the old one, immediately invalidating its subsequent access and media
requests. The link lasts 72 hours from creation and grants a retention lease for
that one completed job and MP4. Unshared jobs retain ordinary 24-hour/configured
retention. An active share lease supersedes ordinary file/completion age and an
ordinary job expiry without rewriting them. A still-active share can be rotated
for a fresh 72-hour lease, but an expired unshared artifact cannot be resurrected.
Sharing never renders another video or extends the lifetime of an existing
ten-minute export/download capability.

Issuance verifies session ownership and validates the current artifact inside
SQLite `BEGIN IMMEDIATE`, including any existing active lease. Cleanup holds the
same database write reservation from history pruning and protected-path
selection through filesystem unlink. These operations serialize across separate
Database objects/processes: if issuance wins, cleanup preserves its job and file;
if cleanup wins, creation cannot return a link to the removed artifact. Revocation
ends the extension immediately, and normal cleanup removes the file/history once
their ordinary retention has passed. Explicit history deletion invalidates the
share immediately and leaves the orphaned file for that same ordinary cleanup.

The standalone viewer is public and does not require or create an owner session.
It uses only same-origin assets, no analytics or third-party resources, a
restrictive CSP, no-referrer, private/no-store and noindex headers. Its fragment
never enters an HTTP URL or Referer header. The viewer posts the bearer in a
bounded URL-encoded body to `POST /api/shares/{job_id}/access`. Valid access sets
an HttpOnly, SameSite=Strict capability cookie scoped to `/api/shares/{job_id}`,
Secure on HTTPS (or when secure cookies are configured), and expiring with the
capability. This cookie authorizes only this video, never job history or owner
APIs. Access endpoints never fall back to a browser's owner cookie. Request bodies
and Cookie/Set-Cookie headers must not be logged by deployment middleware.

Native video controls use the token-free `GET /api/shares/{job_id}/video` route;
`HEAD` and byte Range requests are supported for native playback and seeking.
`?download=1` selects an MP4 attachment on that same authorized route. Every
request rechecks the capability digest, expiry, completed video state, artifact
type/existence and current retention deadline. `DELETE
/api/jobs/{job_id}/share-link` verifies ownership and revokes the capability.
Deleting history removes it atomically, and retention cleanup removes expired
and orphaned records. Revocation blocks subsequent requests; it cannot erase
bytes already downloaded or buffered during an earlier authorized request.

The single-process demo bounds access exchanges to 60 per peer per minute and
600 total per minute. Only ephemeral keyed peer digests are kept in its bounded
in-memory limiter. A future multi-process deployment needs a shared edge limiter.
Native media/Range requests are deliberately outside that limiter, so ordinary
seeking is not mistaken for repeated link exchange. Malformed/oversized token
bodies and unavailable capabilities return generic errors without echoing tokens
or private job metadata.

Playback requires an explicit user action, with no autoplay. Fragment changes
and page dismissal abort pending access and unload the old video; older responses
cannot restore stale media. Back/forward-cache restoration revalidates access.
The viewer unloads media at the advertised expiry and gives retry/recovery
guidance for expired, revoked, removed or unplayable videos. WeChat users see
browser-menu and copy-to-Safari/Chrome guidance. The fragment is preserved so that
manual handoff and explicit copy retain access. Browser history and the clipboard
may consequently retain the bearer link; forwarding it grants the same limited
access. There is no fake button that claims to launch Safari or save into Photos.

Regression coverage: `tests/python/test_video_shares.py` and
`tests/frontend-video-share-viewer.test.mjs`. Browser DOM tests do not replace a
physical WeChat/iPhone playback, browser-menu and native-download check.

## WeChat iPhone video download handoff

A WeChat download click opens recovery guidance, even when the first-visit notice
has been dismissed. Ordinary browsers retain direct session-owned downloads and
inline playback is unchanged. Opening the recovery dialog alone creates no link.
The user explicitly chooses **建立 10 分鐘影片連結** after seeing the privacy notice.
`POST /api/jobs/{job_id}/export-link` verifies the browser owns a completed render
with an existing non-symlink MP4. It creates a 256-bit random capability for that
single artifact; SQLite stores only its SHA-256 digest and expiration. A new link
replaces the previous link for that job. Expiry is the earliest of ten minutes,
ordinary retention (24 hours or configured shorter retention, completion age and
file age), or an active share's extended retention deadline when applicable.
A video retained by a live 72-hour share still supports a separate ten-minute
export link. Export access rechecks the current retention lease; revoking that
share invalidates exports that depended on its extension, while ordinary retained
files keep their existing export behavior. Creating an export does not grant or
renew a share lease, render another video, or transfer a session cookie.

The returned relative URL uses `/export.html#job_id.token`. The fragment is not
sent in HTTP requests or Referer headers; the landing page has no third-party
resources, a restrictive CSP and no-referrer policy. It opens a standalone artwork
page with native playback and download controls, using the same player code and
styles as the 72-hour shared viewer; its copy notice and expiry remain ten minutes. The user copies the link to
Safari/Chrome or manually uses WeChat's browser menu when available. There is no
fake “Open Safari” button. The landing page preserves the fragment for that menu
handoff. A same-origin fetch posts the fragment token in a bounded URL-encoded
body to `/api/exports/{job_id}/access`. Valid access sets a separate HttpOnly,
SameSite=Strict cookie scoped to `/api/exports/{job_id}`, Secure on HTTPS or when
configured, and bounded by the original export capability and retention deadline.
Native GET/HEAD `/api/exports/{job_id}/video` handles playback and Range requests;
`?download=1` streams an attachment without buffering the MP4 in JavaScript.
Every media request rechecks the original export digest, expiry and artifact.
The export cookie never authorizes a 72-hour share, another video, or owner APIs.
Opening the page neither creates a share lease nor extends export retention.
The older body-token POST `/api/exports/{job_id}/download` remains available to
API clients, but the browser page no longer submits a native form. Under
no-referrer, native form navigation can send `Origin: null`, which the existing
same-origin guard correctly rejects. Fetch exchange keeps a verifiable origin;
null and foreign origins remain rejected. No CORS or origin exception is added.
Access logs must not record request bodies or Cookie/Set-Cookie headers.
Responses remain private/no-store, no-referrer and noindex.

Possession of the link authorizes watching and downloading only this MP4, without history or
other job access. The endpoint rechecks hash, expiry, completion, artifact type,
file existence and retention. Owners can revoke via
`DELETE /api/jobs/{job_id}/export-link`; deleting history also removes the
capability, and normal cleanup prunes expired/orphaned capabilities. Revocation
blocks subsequent requests, not an already-started download. Browser history and
clipboard may retain the bearer link, so the UI warns against forwarding it.
Create/revoke actions are serialized across dialog dismissal and reopening.

Regression coverage: `tests/python/test_video_exports.py` and
`tests/frontend-video-export.test.mjs`; the shared viewer DOM suite runs
for both 10-minute export and 72-hour share pages. A physical iPhone/WeChat-to-Safari download
still needs on-device validation; DOM/API tests cannot verify OS download handling
or promise that a video will save directly into Photos.
