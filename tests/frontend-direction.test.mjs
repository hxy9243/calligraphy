import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const exportResponse = ({ url }) => {
  if (url === '/api/previews') return jsonResponse({ preview_url: '/fixtures/preview.png' });
  if (url === '/api/renders') return jsonResponse({ job_id: 'vid_test', status: 'queued' }, 202);
};

async function requestBothExports(ui) {
  ui.document.getElementById('btn-preview').click();
  await flush();
  ui.document.getElementById('btn-render').click();
  await flush();
  return ui.requests.filter(request => ['/api/previews', '/api/renders'].includes(request.url));
}

function assertControls(ui, direction) {
  const vertical = direction === 'vertical-rl';
  const stage = ui.document.getElementById('calligraphy-stage');
  assert.equal(stage.classList.contains('vertical'), vertical);
  assert.equal(stage.classList.contains('horizontal'), !vertical);
  for (const [id, active] of [['btn-vertical', vertical], ['btn-horizontal', !vertical]]) {
    const button = ui.document.getElementById(id);
    assert.equal(button.classList.contains('active'), active);
    assert.equal(button.getAttribute('aria-pressed'), String(active));
  }
}

test('horizontal selection is shared by the stage, preview, video and persisted reload', async t => {
  const ui = await createFrontend({ fetch: exportResponse });
  t.after(ui.close);
  assertControls(ui, 'vertical-rl');
  ui.document.getElementById('btn-horizontal').click();
  assertControls(ui, 'horizontal-lr');
  const requests = await requestBothExports(ui);
  assert.equal(requests.length, 2);
  for (const request of requests) assert.equal(request.body.direction, 'horizontal-lr');
  const savedDirection = ui.window.localStorage.getItem('calligraphy.direction');
  assert.equal(savedDirection, 'horizontal-lr');

  const reloaded = await createFrontend({ fetch: exportResponse, setup(window) {
    window.localStorage.setItem('calligraphy.direction', savedDirection);
  } });
  t.after(reloaded.close);
  assertControls(reloaded, 'horizontal-lr');
  for (const request of await requestBothExports(reloaded)) assert.equal(request.body.direction, 'horizontal-lr');

  reloaded.document.getElementById('btn-vertical').click();
  assertControls(reloaded, 'vertical-rl');
  assert.equal(reloaded.window.localStorage.getItem('calligraphy.direction'), 'vertical-rl');
  reloaded.document.getElementById('btn-preview').click();
  await flush();
  assert.equal(reloaded.requests.filter(request => request.url === '/api/previews').at(-1).body.direction, 'vertical-rl');
});

for (const savedDirection of [null, 'diagonal', 'vertical-rl']) {
  test(`default/invalid saved direction ${JSON.stringify(savedDirection)} exports vertically`, async t => {
    const ui = await createFrontend({ fetch: exportResponse, setup(window) {
      if (savedDirection !== null) window.localStorage.setItem('calligraphy.direction', savedDirection);
    } });
    t.after(ui.close);
    assertControls(ui, 'vertical-rl');
    const requests = await requestBothExports(ui);
    assert.equal(requests.length, 2);
    for (const request of requests) assert.equal(request.body.direction, 'vertical-rl');
  });
}

test('direction controls and exports work when browser storage is blocked', async t => {
  const ui = await createFrontend({ fetch: exportResponse, setup(window) {
    Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage blocked'); } });
  } });
  t.after(ui.close);
  assertControls(ui, 'vertical-rl');
  ui.document.getElementById('btn-horizontal').click();
  assertControls(ui, 'horizontal-lr');
  for (const request of await requestBothExports(ui)) assert.equal(request.body.direction, 'horizontal-lr');
});

test('switching a restored horizontal layout back to vertical updates both exports', async t => {
  const ui = await createFrontend({ fetch: exportResponse, setup(window) {
    window.localStorage.setItem('calligraphy.direction', 'horizontal-lr');
  } });
  t.after(ui.close);
  ui.document.getElementById('btn-vertical').click();
  assertControls(ui, 'vertical-rl');
  const requests = await requestBothExports(ui);
  assert.equal(requests.length, 2);
  for (const request of requests) assert.equal(request.body.direction, 'vertical-rl');
});
