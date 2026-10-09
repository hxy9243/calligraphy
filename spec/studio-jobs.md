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
encoding. Terminal history and output files expire after 24 hours; cleanup also
removes expired files whose history was previously deleted.

## Browser behavior

Clicking Render submits immediately. Only the HTTP submission disables the Render
button; it becomes available again as soon as the request succeeds or fails. The
editor and preview controls remain usable while queued work runs. Validation and
submission errors can appear by the form because no accepted job exists yet.

After acceptance the job list refreshes. Each job card displays its own queued,
rendering/running percentage, completed or failed status. Failed cards contain
the associated error; completed video cards offer Play and Download. Render
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
appear in history or provide status/download access. Output files remain on disk until the 24-hour retention cleanup;
this action deletes history without changing file retention. The browser reports
errors in the confirmation dialog and permits retry, refreshes counts after
success, and rejects list responses captured before deletion.
