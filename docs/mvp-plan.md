# Public calligraphy studio: MVP implementation plan

Date: 2026-09-27  
Status: implementation proposal; only the engine directory move is implemented in this change.

## Outcome and agreed direction

Anyone can open the site without creating an account, enter Chinese text, choose
a published font style, customize a composition, preview the writing and request
an asynchronous MP4. An authenticated administrator manages styles and derived
glyph caches. Use one production repository; keep research in `calligraphy-lab`.

The engine lives directly in `calligraphy/`, while the installed package remains
`calligraphy-engine` and Python imports remain `calligraphy`. Python will own
preparation, layout, timing, caches and exports. JavaScript owns the browser UI
and display, with no Node server required at runtime. The engine remains usable
without the web application. Existing local changes are preserved.

The original account-based proposal is superseded: no signup, user profiles,
cloud project library, billing or cross-device identity in this MVP. Admin
authentication is separate from anonymous visitor access.

## MVP scope and provisional limits

These are initial engineering defaults to benchmark and tune, not measurements
or guarantees of current performance.

| Area | First release |
| --- | --- |
| Input | 1–80 Han characters; preserve traditional/simplified distinction; explicit newline and punctuation break/omit policies |
| Styles | At least two vetted font-derived styles, with declared font and stroke-guide coverage; no silent fallback |
| Layout | One page; vertical right-to-left and horizontal left-to-right; line length, margins, character spacing and line spacing |
| Appearance | Background and ink colours, plain/textured paper, border and a curated decorative seal |
| Glyph adjustments | Global scale 0.8–1.2, horizontal stretch 0.9–1.1 and rotation ±5 degrees; validate transformed bounds |
| Timing | Playback speed 0.5–2, inter-character pauses, intro/outro; reject settings exceeding output limits |
| Preview | Completed still, selected partial frames and an explicitly requested low-resolution writing preview |
| Export | PNG and H.264 MP4; presets up to 1280 pixels on the long edge, even dimensions, 24 fps and 120 seconds |
| Retrieval | Same-browser anonymous session and job list; successful outputs retained for 24 hours |
| Admin | Add/inspect/publish/disable style revisions, prewarm glyphs, inspect/rebuild/evict derived caches and inspect failed jobs |

Font thickness editing, freehand stroke editing, arbitrary uploaded decorations,
public font uploads, multiline multilingual typesetting, pagination, music,
public galleries and collaboration are deferred. “Any text” means supported Han
text within the selected style's font-and-guide coverage, not all Unicode.

Only publish fonts and decorations cleared for the intended hosted use. Local
registration alone does not make an asset eligible for public distribution.
Raw font files remain private; public APIs do not return local paths or font files.

## Repository and deployment boundaries

```text
calligraphy/            Python engine package; import calligraphy
backend/                API, database models, queue tasks and admin authorization
frontend/               Public editor and admin UI; SVG/image/video display
styles/                 Small style descriptors and provenance, no generated banks
deploy/                 Containers, local service setup and hosting configuration
tests/                  Engine, API, worker, browser and packaging checks
spec/                   Implemented component contracts
docs/mvp-plan.md         Proposed implementation milestones
```

Use a Python API (proposed: FastAPI), a React/Vite frontend build served by the
API, PostgreSQL, Redis-backed jobs (proposed: Celery), a Python worker and private
S3-compatible object storage. These framework selections are implementation
defaults, not requirements to rewrite useful existing modules.

Deploy web/API and worker separately from the same container image and revision.
Node is needed to build browser assets, not to render video. Start with one
worker process and one expensive task at a time. Store temporary frames on local
scratch disk; durable fonts, glyph assets and outputs belong in object storage.
PostgreSQL is the job and metadata authority; Redis transports tasks and limits
requests. Losing Redis must not silently lose accepted jobs.

Railway is the initial deployment target. Its worker/queue and bucket patterns
fit this design. Do not use a service-mounted volume as a multi-worker shared
glyph store: Railway currently disallows replicas with volumes. Provision and
launch hosting only as a later implementation milestone; this plan provisions
no services and incurs no hosting charges.

## Engine and preview contract

Port text parsing, coverage resolution, layout and timing to Python before
building application-specific versions. Preserve the existing behavior with
fixture comparisons; retain JS compatibility entry points during migration.
Explicitly separate horizontal/vertical layout gaps from timing gaps.

Normalize CRLF/CR to newline, retain nonempty explicit lines and drop blank lines.
Ignore other whitespace without reserving blank cells. Count Han Unicode code
points after normalization, including repetitions; only the explicit punctuation
set in the current parser is supported. Under `break`, punctuation starts a new
line but consumes no glyph or writing time; under `omit`, it is skipped entirely.
Unsupported characters reject the whole request with a list of offending symbols.
Keep the original text alongside the normalized representation within retention.
Global glyph controls apply to every placement; per-character editing is deferred.

Define a versioned SceneSpec containing normalized text, style revision,
page dimensions, colours, decoration IDs and checksums, transforms and timing.
At admission, save an immutable SceneSpec and pin preparation inputs/versions.
After any missing glyph preparation completes, Python atomically finalizes an
immutable RenderPlan with exact glyph artifact hashes, renderer version, resolved
positions, stroke schedules and duration, and pins all referenced artifacts.
Rendering retries reuse that plan; admin rebuilds and overrides never replace
its references. Preparation retries use the pinned input recipe. Edits after
submission create a new snapshot, never mutate a running render.

Promote the font-preserving output script into a reusable engine implementation:
store canonical target masks, overlapping stroke layers and progression fields.
The max-composite at completion must match the canonical target mask. This is a
shape guarantee, not evidence of authentic stroke motion or pixel identity after
rescaling/video encoding. Keep contact-brush rendering as a separate explicit mode.

The Python frame renderer is authoritative for previews and exports. SVG in the
browser hosts prepared images and decorations; it does not require vectorizing
all glyph masks. Reuse vector paths for existing vector modes where appropriate.
The first hosted font preview uses a server-rendered still and a short MP4 for
playback/seeking. Animated previews cover the first 15 seconds of scene time (or
the whole scene if shorter), at a maximum 480-pixel long edge and 12 fps. Return
the explicit scene time range and label excerpts; stills may sample the full
scene including exact completion. Do not transfer hundreds of full-resolution
frames to the browser.

Debounce still requests, cap their rate and discard responses for older editor
revisions. Colour/placement controls may show a provisional browser composition;
replace it with the authoritative preview before export. No separate frontend
stroke inference or authoritative layout algorithm. Rendering occurs through the
worker, not inside a long-running HTTP handler.

## Styles, preparation and caches

### Shared character-guide cache (Make Me a Hanzi / Hanzi Writer Data)

Add a persistent, style-independent cache for ordered stroke outlines and median
paths. The current resolver downloads Hanzi Writer Data 2.0.1 records and returns
them in memory; the new cache makes those guides reusable across fonts, jobs and
restarts. Record Make Me a Hanzi lineage separately from the actual distribution
provider/version; do not assume records from different distributions are identical.

Key lookups by provider, pinned dataset release or commit, character code point
and normalization-schema version. Store immutable raw record bytes with SHA-256,
validated ordered `strokes`/`medians`, source URL and license/provenance records.
Keep simplified and traditional characters distinct. Font fitting consumes an
exact guide hash, so an upstream refresh creates a new guide revision and new
derived glyph keys without changing pinned jobs.

Resolve guides in this order: an explicitly supplied validated local record,
the pinned persistent cache, bundled records, then the allowlisted pinned upstream
when fetching is enabled. Persist successful bundled/fetched resolutions; explicit
local overrides use their own provider namespace and never overwrite upstream
records. No network access is allowed during frame rendering. Local offline runs
fail with the exact missing characters instead of fetching implicitly.

Support bounded batch prewarming and deduplicate concurrent requests for the same
guide. Validate before atomic publication. Distinguish an upstream not-found
result (short negative-cache TTL) from network failure (bounded retry/backoff);
neither becomes a permanent unsupported-character verdict. Administrators can
inspect source revision, coverage, bytes and failures, prewarm a text/character
set, refresh to a new pinned dataset revision and evict unreferenced records.
Guide-cache eviction is separate from font-derived mask-cache eviction; preserve
guide records referenced by retained style revisions and jobs.

This cache supplies canonical stroke order and paths, not style-specific motion.
Font coverage and inferred-animation quality checks still apply independently.

### Font-derived assets

Style revision states: draft → preparing → review → published → disabled.
Each revision pins font bytes/hash, guide source/version, engine preparation
version, parameters, provenance, display name and coverage policy. Publishing a
revision is an admin action after inspecting representative finished and partial
glyphs. A new font or preparation algorithm creates a new revision.

Prewarm a bounded common-character set and a small representative suite (thin
strokes, crossings, disconnected pieces and dense glyphs). Prepare additional
covered characters on demand under the same job limits. A failed or flagged fit
does not silently substitute another style: block export for that character and
show a useful message; admins may review and approve an explicit override tied
to that glyph revision. Unsupported input fails preflight before rendering.

| Artifact | Identity and retention |
| --- | --- |
| Source font | Content hash; retained for referenced style revisions |
| Shared character guide | Provider + dataset revision + character + schema version; immutable record hash pinned by downstream assets |
| Prepared glyph | Hash of font/face, character, guide bytes, algorithm version, raster settings and fitting parameters |
| Preview | Hash of canonical SceneSpec, exact glyph revisions, renderer version and preview profile; short TTL |
| Video | Same plus output settings; private job-scoped output, 24-hour retention |

Cache masks, phases, diagnostic metrics and provenance; do not use only a style
name or Unicode character as the key. Keep colour, background, speed and page
placement out of the preparation key. Repeated characters share prepared assets.
Use immutable objects plus database references; checksum assets when loading.

Deduplicate preparation with a unique glyph key and database lease. Upload a
complete artifact, then publish its metadata transactionally. Expired leases can
be retried; another job must never consume a partial artifact. Count failures and
back off repeated bad glyph requests. Scratch files are disposable.

Cache administration distinguishes invalidate/rebuild, evict derived data,
disable style and delete source. A dry-run deletion lists bytes and dependencies.
Pin assets used by active jobs; garbage collection skips pinned references.
Published revisions retain source material needed to rebuild. Originals are
never deleted by “clear cache.” User content is not a public cache index.

## Anonymous access and cost controls

Create a random server-side anonymous session, referenced by a Secure, HttpOnly,
SameSite cookie. A job belongs to that session; unguessable job IDs alone do not
authorize reads, cancellation or downloads. Enforce ownership on every endpoint.
Protect cookie-authenticated mutations with origin/CSRF checks. Use same-origin
frontend/API hosting for the first release.

Visitors can close the tab and recover jobs on the same browser until expiry.
Cleared cookies or another device do not recover access. Communicate this before
submission. Store editor drafts locally with a clear/reset action; do not promise
account-like durable storage. No transferable recovery links in the first release.

Suggested starting limits: one active render per session, five submissions per
session/hour, a separate IP-based ceiling, ten queued expensive jobs globally,
and one executing worker task. Enforce text, duration, pixel, stroke and number
of newly prepared glyph limits server-side. Preview and preparation requests
also consume budgets. Session cookies alone are not abuse prevention; combine
limits with server-verified bot challenges at expensive submission and a global
daily compute allowance. Configure trusted proxy handling rather than accepting
arbitrary forwarded IP headers. Return retry guidance when capacity is exhausted.

Reserve compute allowance atomically before dispatch, track actual runtime and
release unused reservations on completion/failure. Set a per-task wall-clock and
memory limit. Begin with a configurable ten-minute task deadline, tune it from
benchmarks, and provide an admin pause switch. A session reset or distributed
traffic must not bypass the global queue/compute ceiling.

Admin login uses a maintained authentication integration with an explicit admin
allowlist; no public signup or registration API. All style/cache mutations need
server-side authorization and audit entries. Uploaded fonts are parsed only in
resource-limited worker processes, with size/type limits. Only admin-approved
assets are composited. No arbitrary URLs, filesystem paths, SVG markup or shell
commands are accepted in public render parameters.

## Jobs, persistence and API boundaries

Suggested database entities: anonymous_sessions, styles, style_revisions,
glyph_artifacts, jobs, job_attempts, artifact_references and admin_events.
Keep text and tokens out of routine logs; log IDs, timings and error categories.

Jobs progress through queued → preparing → rendering → uploading → succeeded;
terminal alternatives are failed or cancelled. Output expiry is tracked separately.
Report stages and completed/total glyphs or frames rather than fabricated ETAs.

Persist job and dispatch record in one database transaction. A dispatcher retries
unpublished records; workers claim attempts with leases, heartbeat while running
and use idempotent artifact writes. After restart, reclaim expired attempts.
Allow two retries for transient storage/process failures; invalid input and bad
fits fail without automatic retry. A stale worker must not overwrite a newer
attempt's result. Publish success only after the uploaded video is verified.

Cancel queued work immediately; running tasks check cancellation between glyphs
and frame batches, stop FFmpeg and remove incomplete outputs. Cancelled or expired
attempts cannot publish success. One worker task must not synchronously wait for
a child task on the same single-worker queue: prepare missing glyphs inline or
release the task while dependencies are pending. Low-priority admin prewarming
runs in bounded batches and yields to visitor work.

| Public API | Purpose |
| --- | --- |
| GET /api/styles | Published style descriptions and revision IDs |
| POST /api/preflight | Validate SceneSpec, coverage, duration and limits without fitting |
| POST /api/previews | Queue/cache bounded still or animation preview |
| POST /api/renders | Accept immutable snapshot; return job ID, 202, and expiry policy |
| GET /api/jobs, GET /api/jobs/{id} | Same-session history and progress; polling initially |
| POST /api/jobs/{id}/cancel | Request cancellation with ownership check |
| GET /api/jobs/{id}/download | Authorize and return a short-lived signed object URL |

Previews are typed jobs using the same status, ownership and cancellation APIs.
POST /api/previews returns 202 with a job ID and editor revision, including for a
cache hit (the returned job is already succeeded). Result metadata identifies
the still or MP4 artifact, dimensions, sampled time/range and expiry. Preview
artifacts expire after one hour. Each session may have one export and one preview
pending; coalesce queued previews to its newest editor revision, cancel obsolete
running work at safe checkpoints, and ignore obsolete responses in the UI.
Use separate bounded queues: prefer exports but admit at most one pending preview
between exports, and never preempt an active export. Preview admission has a
separate per-session/IP rate ceiling and shares the global compute allowance.
Admin prewarming runs only when neither visitor queue has pending work.

Use submission idempotency keys scoped to the session. Poll with backoff; SSE is
optional later. Short-lived signed URLs are bearer links and expire promptly;
bucket credentials are never exposed. Jobs from two anonymous sessions remain
isolated even when their glyph preparation is shared.

Expire export outputs 24 hours after success, failed-job text after 24 hours and idle
anonymous sessions after seven days. Cleanup removes objects and sensitive job
payloads; retain only bounded non-content operational aggregates. Retention limits
bound reproducibility: a manifest pins exact inputs while its referenced assets
remain retained, not a promise of indefinite regeneration or byte-identical MP4s.

## Ordered implementation milestones

Each milestone should be a reviewable change with its stated acceptance checks.
Do not combine the renderer rewrite and full editor into one large change.

### M0 — Engine directory and package compatibility

- [x] Move `python/calligraphy/` to `calligraphy/`, preserving local edits and import name.
- [x] Update package configuration and current documentation paths.
- [x] Verify editable install, wheel contents, installed asset lookup and lab regressions.

Done when existing consumers import `calligraphy` without changing their code,
and package assets work outside the checkout. Leave historical migration reports
as historical records; keep the existing local notebook in place.

Validation on 2026-09-27: 33 JavaScript tests, 35 Python tests and 24 downstream
lab tests passed. A built wheel imported from outside the repository and loaded
all three bundled contact banks. M0 is complete; M1–M6 remain planned.

### M1 — One Python text-to-video pipeline

- [x] Port text validation, glyph resolver, layout and schedule from JS to engine modules.
- [x] Add versioned SceneSpec/RenderPlan and a Python CLI.
- [x] Promote font-preserving masks/phases into the engine; share still/video frames.
- [x] Add explicit styling/transforms and preserve template/contact compatibility.

Done when local text + a registered font produces PNG/MP4 without Node, repeated
glyphs share assets, known partial frames are correct and final masks reconstruct
the source. Compare JS/Python parsing, placement and schedules on fixed fixtures.
Test zero-outro completion, unsupported glyphs, bounds and backward seeking.

Validation on 2026-09-27: 33 JavaScript tests, 52 Python tests and 24 downstream
lab tests passed. Python CLI rendered still PNG, SVG and H.264 MP4 without Node;
font-preserving layer decomposition achieved exact source reconstruction (error 0.0);
cross-language plan comparisons produced identical coordinates and timing. M1 is complete.

### M2 — Versioned styles and reusable artifact storage

- [ ] Add the shared character-guide cache, versioned provider adapter, validation,
  offline resolution, negative-cache expiry and admin prewarming hooks.
- [ ] Implement local and object-storage adapters, glyph keys and diagnostic records.
- [ ] Import existing banks as explicit legacy revisions; do not mistake old contact
  geometry for new exact-mask artifacts.
- [ ] Add revision-aware preparation, leases, invalidation, pins and cache inspection.
- [ ] Benchmark cold preparation, warm render time, peak memory and storage per glyph.

Done when a warm run performs zero preparation, a changed guide invalidates the
correct glyph, concurrent identical requests fit once, and interrupted preparation
cannot expose partial files. Background/spacing changes must reuse glyph assets.
Verify that two different fonts reuse the same cached character guide without
another download, restarts preserve it, local overrides cannot replace upstream
records, invalid downloads never publish, and missing-data TTLs expire correctly.

### M3 — First hosted end-to-end path

- [ ] Add API, PostgreSQL, queue, worker and object storage with local service setup.
- [ ] Implement anonymous sessions, job ownership, immutable submissions, recovery,
  cancellation, short-lived downloads and retention cleanup.
- [ ] Add admission limits/global budget before exposing rendering publicly.
- [ ] Build a minimal text/style form and job result page using one vetted style.
- [ ] Deploy a restricted staging environment on Railway.

Done when a visitor can submit, close/reopen the tab and download a verified MP4;
worker restart recovers accepted work; duplicate submissions are idempotent; a
different session cannot inspect/cancel/download the job. Verify queue-full,
storage-failure, timeout and output-expiry behavior. Staging is not public launch.

### M4 — Composition editor and previews

- [ ] Add layout, spacing, colour, timing and bounded glyph-transform controls.
- [ ] Add curated paper, border and seal layers with safe placement defaults.
- [ ] Add debounced still previews, partial-frame checks and low-resolution playback.
- [ ] Add browser-local drafts, job history, retry messages and expiry notices.

Done when preview and export use the same scene revision, stale previews cannot
overwrite newer ones, decorations do not clip transformed glyphs, and mobile/desktop
editing work. Verify a representative set of preview frames against export frames
allowing declared scale/codec differences. All server limits also apply to previews.
Test rapid edits to confirm preview coalescing, excerpt labeling, ownership,
expiry and that preview traffic cannot starve export jobs.

### M5 — Admin styles and cache management

- [ ] Add admin authentication/authorization and style upload/revision workflows.
- [ ] Add coverage, diagnostic and partial-animation inspection before publication.
- [ ] Add bounded prewarming, pause/resume, cache size/usage and failed-job inspection.
- [ ] Add dry-run eviction/rebuild actions, reference protection and audit history.
- [ ] Publish at least two vetted styles, with asset-use records and sample text.

Done when an admin can add a style without a code deployment, visitors see only
published revisions, a disabled style stops new jobs while accepted jobs finish,
and clearing unpinned cache rebuilds safely without deleting source fonts.

### M6 — Public launch checks and operations

- [ ] Pin dependencies/container tools and record renderer/asset versions per job.
- [ ] Add CI for calligraphy/backend/frontend, packaging and relevant downstream lab checks.
- [ ] Configure private storage/networking, admin identity, secrets and health checks.
- [ ] Exercise two-session isolation, queue saturation, restart/cancellation and cleanup.
- [ ] Test database backup/restore and pin-compatible rollback; deploy staging then production.
- [ ] Measure render CPU time, cold/warm latency, peak memory, failure rate, queue depth,
  cache hit rate and storage growth; set initial quotas from observed workload/cost.
- [ ] Publish concise input limits, retention, privacy and inferred-motion explanations.

Done when a clean deployment completes the full anonymous flow with both styles,
survives worker restart, rejects excess work predictably and stays within the
configured compute/storage allowance. Do not publish a monthly cost estimate
until real workloads are measured.

## First implementation target and decision checkpoints

After M0, start M1 with a small regression fixture spanning repeated characters,
both writing directions, thin strokes and overlaps. The first demo is one font,
one short poem and one Python command producing a still plus an MP4. Build the
hosted slice only after this engine contract is stable.

Before staging: choose admin identity provider and confirm eligible initial font
assets. Before public launch: measure worker sizing, select a hosting spend ceiling
and tune the provisional limits. These decisions do not block local M1/M2 work.
The current plan authorizes no account creation, hosting purchase or deployment.

## Sources and evidence

- Current implementation: `scripts/render-text.mjs`, `src/text/`, `calligraphy/font_pipeline.py`,
  `calligraphy/font_fitting.py`, `calligraphy/contact_renderer.py` and existing regression suites.
- Font-preserving prototype: the local project's `output/shoujin-yinjiu/render_font_preserving.py`;
  extract its reusable logic and remove output-folder/global-state assumptions.
- [Railway workers and queues](https://docs.railway.com/guides/cron-workers-queues).
- [Railway volumes and replica limitations](https://docs.railway.com/volumes/reference).
- [Railway object storage](https://docs.railway.com/data-storage).
- Hosting documentation checked 2026-09-27. Product limits and framework selections
  above are proposed defaults, not existing implemented behavior.
