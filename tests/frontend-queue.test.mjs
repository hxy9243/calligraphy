import assert from 'node:assert/strict';
import test from 'node:test';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const deferred = () => {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
};

const renderJob = (overrides = {}) => ({
  job_id: 'vid-one', job_type: 'render', text: '永', style: 'kai',
  status: 'queued', progress: 0, created_at: '2026-01-01T12:00:00Z',
  ...overrides,
});

const badge = (document, jobId = 'vid-one') =>
  document.querySelector(`[data-job-id="${jobId}"] .job-status-badge`);

const assertNoInlineRenderStatus = document => {
  assert.equal(document.getElementById('status-message').classList.contains('hidden'), true);
  assert.doesNotMatch(document.getElementById('status-message').textContent, /书写视频渲染中/);
};

test('Render disables only submission, queues directly, and repeated accepted clicks show one active card', async t => {
  const submitted = deferred();
  const jobs = [];
  let submissions = 0;
  const ui = await createFrontend({
    jobs,
    fetch: ({ url, body }) => {
      if (url === '/api/renders') {
        submissions++;
        assert.equal(body.text, '永');
        if (submissions === 1) return submitted.promise;
        return jsonResponse({ job_id: 'vid-one', status: 'queued' }, 202);
      }
    },
  });
  t.after(ui.close);
  const { document, window } = ui;
  const button = document.getElementById('btn-render');
  document.getElementById('text-input').value = '永';
  button.click();
  assert.equal(button.disabled, true);
  assert.equal(document.getElementById('btn-preview').disabled, false);
  button.dispatchEvent(new window.Event('click'));
  assert.equal(submissions, 1);
  jobs.push(renderJob());
  submitted.resolve(jsonResponse({ job_id: 'vid-one', status: 'queued' }, 202));
  await flush();
  assert.equal(button.disabled, false);
  assert.equal(badge(document).textContent, '排队中');
  assertNoInlineRenderStatus(document);
  button.click();
  await flush();
  assert.equal(submissions, 2);
  assert.equal(document.querySelectorAll('.job-item').length, 1);
  assert.equal(ui.timeouts.size, 1, 'repeated submissions share a single refresh timer');
});

test('accepted renders release the form without waiting for a slow job-history refresh', async t => {
  const slowList = deferred();
  let listCalls = 0;
  const ui = await createFrontend({
    fetch: ({ url }) => {
      if (url === '/api/jobs' && ++listCalls > 1) return slowList.promise;
      if (url === '/api/renders') return jsonResponse({ job_id: 'vid-one', status: 'queued' }, 202);
    },
  });
  t.after(ui.close);
  const button = ui.document.getElementById('btn-render');
  button.click();
  await flush();
  assert.equal(button.disabled, false);
  assert.equal(ui.document.getElementById('btn-preview').disabled, false);
  assertNoInlineRenderStatus(ui.document);
  slowList.resolve(jsonResponse({ jobs: [renderJob()] }));
  await flush();
  assert.equal(badge(ui.document).textContent, '排队中');
});

test('job cards own queued/running/completed/failed state and completion does not interrupt editing', async t => {
  const jobs = [renderJob(), renderJob({ job_id: 'vid-two', text: '明' })];
  const ui = await createFrontend({ jobs });
  t.after(ui.close);
  const { document } = ui;
  assert.equal(badge(document).textContent, '排队中');
  jobs[0].status = 'rendering';
  jobs[0].progress = 0.5;
  jobs[1].status = 'running';
  jobs[1].progress = 0.3;
  await ui.tickTimeouts();
  assert.equal(badge(document).textContent, '渲染中 (50%)');
  assert.equal(badge(document, 'vid-two').textContent, '渲染中 (30%)');
  assert.equal(document.getElementById('btn-render').disabled, false);
  assertNoInlineRenderStatus(document);

  document.getElementById('text-input').value = '新的创作';
  document.getElementById('btn-close-export').click();
  jobs[0].status = 'succeeded';
  jobs[0].progress = 1;
  jobs[1].status = 'failed';
  jobs[1].error_message = '<script>render failed</script>';
  await ui.tickTimeouts();
  assert.equal(badge(document).textContent, '完成');
  assert.equal(badge(document, 'vid-two').textContent, '失败');
  assert.equal(document.querySelector('.job-error').textContent, '<script>render failed</script>');
  assert.equal(document.querySelector('.job-error script'), null);
  assert.ok(document.querySelector('[data-job-id="vid-one"] .btn-play-mini'));
  assert.ok(document.querySelector('[data-job-id="vid-one"] .btn-download'));
  assert.equal(document.getElementById('text-input').value, '新的创作');
  assert.equal(document.getElementById('export-output-box').classList.contains('hidden'), true);
  assert.equal(ui.mediaEvents.filter(event => event.method === 'play').length, 0);
  assertNoInlineRenderStatus(document);
  assert.equal(ui.timeouts.size, 0, 'terminal jobs stop refreshing');
  assert.equal(ui.requests.some(request => /\/api\/jobs\//.test(request.url)), false);
});

test('restored active jobs keep refreshing after transient failures and beyond the old three-minute cutoff', async t => {
  const jobs = [renderJob({ status: 'rendering' })];
  let failRefresh = false;
  const ui = await createFrontend({
    jobs,
    fetch: ({ url }) => url === '/api/jobs' && failRefresh ? jsonResponse({}, 503) : undefined,
  });
  t.after(ui.close);
  ui.window.console.warn = () => {};
  assert.equal(ui.timeouts.size, 1);
  failRefresh = true;
  await ui.tickTimeouts();
  assert.equal(ui.timeouts.size, 1);
  assert.equal(badge(ui.document).textContent, '渲染中 (0%)');
  failRefresh = false;
  for (let tick = 0; tick < 181; tick++) await ui.tickTimeouts();
  assert.equal(ui.timeouts.size, 1);
  assertNoInlineRenderStatus(ui.document);
  jobs[0].status = 'succeeded';
  await ui.tickTimeouts();
  assert.equal(badge(ui.document).textContent, '完成');
  assert.equal(ui.timeouts.size, 0);
});

test('submission errors release the button, and an accepted retry resumes job refresh after a list failure', async t => {
  let submissions = 0;
  let failList = false;
  const jobs = [];
  const ui = await createFrontend({
    jobs,
    fetch: ({ url }) => {
      if (url === '/api/renders') {
        if (++submissions === 1) return jsonResponse({ detail: '暂时无法提交' }, 503);
        jobs.push(renderJob());
        failList = true;
        return jsonResponse({ job_id: 'vid-one', status: 'queued' }, 202);
      }
      if (url === '/api/jobs' && failList) return jsonResponse({}, 503);
    },
  });
  t.after(ui.close);
  ui.window.console.warn = () => {};
  const button = ui.document.getElementById('btn-render');
  button.click();
  await flush();
  assert.equal(button.disabled, false);
  assert.match(ui.document.getElementById('status-message').textContent, /提交失败: 暂时无法提交/);
  button.click();
  await flush();
  assert.equal(button.disabled, false);
  assertNoInlineRenderStatus(ui.document);
  assert.equal(ui.timeouts.size, 1);
  failList = false;
  await ui.tickTimeouts();
  assert.equal(badge(ui.document).textContent, '排队中');
});

test('older list responses cannot erase a new accepted render', async t => {
  const oldList = deferred();
  let listCalls = 0;
  const ui = await createFrontend({
    fetch: ({ url }) => {
      if (url === '/api/jobs') {
        if (++listCalls === 1) return oldList.promise;
        return jsonResponse({ jobs: [renderJob()] });
      }
      if (url === '/api/renders') return jsonResponse({ job_id: 'vid-one', status: 'queued' }, 202);
    },
  });
  t.after(ui.close);
  ui.document.getElementById('btn-render').click();
  await flush();
  assert.equal(badge(ui.document).textContent, '排队中');
  oldList.resolve(jsonResponse({ jobs: [] }));
  await flush();
  assert.equal(badge(ui.document).textContent, '排队中');
  assert.equal(ui.timeouts.size, 1);
});
