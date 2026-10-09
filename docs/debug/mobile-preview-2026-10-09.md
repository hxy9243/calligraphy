# Mobile preview blanking — 2026-10-09

- Symptom: the live calligraphy preview goes blank while scrolling on mobile.
- Root cause: every window resize calls `fitStage()`, which schedules a backend
  preview, immediately hides the existing PNG, and advances the preview revision.
  Scroll-related viewport changes therefore blank unchanged artwork; repeated
  resizing also rejects otherwise-current responses already in flight.
- Fix: resize still lays out and fits the displayed paper, but calls
  `fitStage(false)` to preserve preview pixels and the current request revision.
  Text/font/canvas changes continue to request new backend previews.
- Evidence: two regressions failed against the original production script:
  height-only resize hid the visible image, and resize discarded an in-flight
  response. Both passed after the fix, along with the four existing font-preview
  tests. Width changes still resize the paper and text edits still fetch pixels.
  The full `npm test` suite passed all 91 tests (0 failures).
- Regression tests: `tests/frontend-font-privacy.test.mjs`, mobile viewport and
  in-flight resize cases; both load the actual production HTML/script.
- Related: backend previews were introduced in `04af414`; the resize handler
  inherited an unconditional preview refresh from display fitting.
- Status: DONE_WITH_CONCERNS. Event-level reproduction is fixed. Actual mobile
  browser rasterization is unverified; desktop browser control previously failed
  its admin policy check, so no alternate browser-control method was used.

Mobile address-bar changes can affect viewport sizing; browser background:
[Chrome URL bar resizing](https://developer.chrome.com/blog/url-bar-resizing/).
The exact event behavior varies by browser. The regression verifies our handler's
response to resize, rather than claiming a device/browser recording.
