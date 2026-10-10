import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const makeJob = (job_id, params, extra = {}) => ({ job_id, job_type: 'render',
  status: 'succeeded', style: 'kai', text: '明月，清泉', params, ...extra });
const complete = { width: 960, height: 720, font_size: 110, fit: false,
  direction: 'horizontal-lr', spacing: 0.42, punctuation: 'break', speed: 1.5, fps: 30 };
const exportResponse = ({ url }) => {
  if (url === '/api/previews') return jsonResponse({ preview_url: '/fixtures/reused.png' });
  if (url === '/api/renders') return jsonResponse({ job_id: 'new', status: 'queued' }, 202);
};
const byId = (ui, id) => ui.document.getElementById(id);
async function reuse(ui, id) {
  ui.document.querySelector(`[data-job-id="${id}"] .job-text`).click();
  assert.equal(byId(ui, 'job-detail').open, true);
  byId(ui, 'detail-reuse').click();
  await flush();
  assert.equal(byId(ui, 'job-detail').open, false);
  assert.equal(ui.window.location.hash, '#create');
}
function assertNumeric(ui, id, value) {
  assert.equal(Number(byId(ui, id).value), value, id);
}
function assertSegment(ui, id, key, value) {
  const active = byId(ui, id).querySelectorAll('.active');
  assert.equal(active.length, 1);
  assert.equal(Number(active[0].dataset[key]), value);
  assert.equal(active[0].getAttribute('aria-pressed'), 'true');
}

test('reuse restores the whole editor and keeps saved dimensions through edits and export', async t => {
  const ui = await createFrontend({ jobs: [makeJob('full', complete)], fetch: exportResponse });
  t.after(ui.close);
  await reuse(ui, 'full');
  assert.equal(byId(ui, 'text-input').value, '明月，清泉');
  assert.equal(byId(ui, 'style-select').value, 'kai');
  assert.equal(byId(ui, 'canvas-dim-val').textContent, '960 × 720');
  assert.equal(byId(ui, 'canvas-len-axis').textContent, '寬度');
  assertNumeric(ui, 'canvas-len-slider', 960);
  assertNumeric(ui, 'size-slider', 110);
  assert.equal(byId(ui, 'size-val').textContent, '110px');
  assertNumeric(ui, 'spacing-slider', 0.42);
  assert.equal(byId(ui, 'spacing-val').textContent, '0.42em');
  assert.equal(byId(ui, 'calligraphy-text').style.letterSpacing, '0.42em');
  assert.equal(byId(ui, 'fit-toggle').checked, false);
  assert.equal(byId(ui, 'punctuation-select').value, 'break');
  assert.equal(byId(ui, 'btn-horizontal').getAttribute('aria-pressed'), 'true');
  assert.equal(byId(ui, 'calligraphy-stage').classList.contains('horizontal'), true);
  assert.equal(ui.window.localStorage.getItem('calligraphy.direction'), 'horizontal-lr');
  assertSegment(ui, 'speed-seg', 'speed', 1.5);
  assertSegment(ui, 'fps-seg', 'fps', 30);
  assert.equal(byId(ui, 'history-reuse-notice').hidden, true);
  assert.equal(ui.document.querySelector('#canvas-formats [data-cf="auto"]').classList.contains('active'), false);

  byId(ui, 'text-input').value = '山水';
  byId(ui, 'text-input').dispatchEvent(new ui.window.Event('input'));
  assert.equal(byId(ui, 'canvas-dim-val').textContent, '960 × 720');
  await ui.tickTimeouts(800);
  const preview = ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body;
  const previewScale = preview.width / 960;
  assert.equal(preview.height, 720 * previewScale);
  assert.equal(preview.font_size, Math.round(110 * previewScale));
  for (const [key, value] of Object.entries({ text: '山水', style: 'kai', direction: 'horizontal-lr', punctuation: 'break', spacing: 0.42, fit: false })) {
    assert.equal(preview[key], value);
  }
  byId(ui, 'btn-render').click();
  await flush();
  const render = ui.requests.find(r => r.url === '/api/renders').body;
  for (const key of ['direction', 'punctuation', 'speed', 'fps', 'spacing']) assert.equal(render[key], complete[key]);
});

test('valid API values outside presets remain exact, visible, editable and replaceable', async t => {
  const custom = { ...complete, width: 128, height: 96, font_size: 8, spacing: 1.25, speed: 2.25, fps: 12 };
  const ui = await createFrontend({ jobs: [makeJob('custom', custom), makeJob('standard', complete)], fetch: exportResponse });
  t.after(ui.close);
  await reuse(ui, 'custom');
  assertNumeric(ui, 'canvas-len-slider', 128);
  assertNumeric(ui, 'size-slider', 8);
  assertNumeric(ui, 'spacing-slider', 1.25);
  assertNumeric(ui, 'speed-select', 2.25);
  assertNumeric(ui, 'fps-select', 12);
  assertSegment(ui, 'speed-seg', 'speed', 2.25);
  assertSegment(ui, 'fps-seg', 'fps', 12);
  assert.equal(byId(ui, 'speed-seg').querySelector('[data-history-value]').textContent, '2.25×（歷史）');
  await ui.tickTimeouts(800);
  const preview = ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body;
  assert.equal(preview.width, 128);
  assert.equal(preview.height, 96);
  assert.equal(preview.font_size, 8);
  assert.equal(preview.spacing, 1.25);
  ui.document.querySelector('#speed-seg [data-speed="1"]').click();
  assertNumeric(ui, 'speed-select', 1);
  ui.document.querySelector('#speed-seg [data-speed="2.25"]').click();
  assertNumeric(ui, 'speed-select', 2.25);
  byId(ui, 'btn-render').click();
  await flush();
  assert.equal(ui.requests.find(r => r.url === '/api/renders').body.speed, 2.25);
  await reuse(ui, 'standard');
  assert.equal(ui.document.querySelectorAll('[data-history-value]').length, 0);
  assertSegment(ui, 'speed-seg', 'speed', 1.5);
});

for (const params of [undefined, {}, { font_size: null }]) {
  test(`legacy settings ${JSON.stringify(params)} use worker defaults and explain unavailable sizing`, async t => {
    const ui = await createFrontend({ jobs: [makeJob('full', complete), makeJob('old', params)] });
    t.after(ui.close);
    await reuse(ui, 'full');
    await reuse(ui, 'old');
    assert.equal(byId(ui, 'canvas-dim-val').textContent, '720 × 960');
    assertNumeric(ui, 'size-slider', 68);
    assert.equal(byId(ui, 'fit-toggle').checked, true);
    assertNumeric(ui, 'spacing-slider', 0.18);
    assert.equal(byId(ui, 'punctuation-select').value, 'omit');
    assert.equal(byId(ui, 'btn-vertical').getAttribute('aria-pressed'), 'true');
    assertSegment(ui, 'speed-seg', 'speed', 1);
    assertSegment(ui, 'fps-seg', 'fps', 24);
    assert.equal(byId(ui, 'history-reuse-notice').hidden, false);
    assert.match(byId(ui, 'history-reuse-notice').textContent, /舊任務未記錄字號.*68px.*外觀可能不同/);
    assert.match(byId(ui, 'status-message').textContent, /可用設定/);
    assert.equal(ui.document.querySelector('#canvas-formats [data-cf="3:4"]').classList.contains('active'), true);
  });
}

test('reuse preserves exact saved text and invalidates even a same-text pending conversion', async t => {
  let resolveConversion;
  const jobs = [makeJob('saved', complete, { text: '鳥', style: 'mashanzheng' })];
  const ui = await createFrontend({ jobs, fetch: ({ url }) => {
    if (url === '/api/styles') return jsonResponse({ styles: [{ id: 'kai', name: 'Kai' }, { id: 'mashanzheng', name: 'Ma' }] });
    if (url === '/api/convert-script') return new Promise(resolve => { resolveConversion = resolve; });
  } });
  t.after(ui.close);
  byId(ui, 'text-input').value = '鳥';
  byId(ui, 'btn-simp').click();
  assert.equal(ui.requests.filter(r => r.url === '/api/convert-script').length, 1);
  await reuse(ui, 'saved');
  assert.equal(byId(ui, 'style-select').value, 'mashanzheng');
  assert.equal(byId(ui, 'text-input').value, '鳥');
  resolveConversion(jsonResponse({ text: '鸟' }));
  await flush();
  assert.equal(byId(ui, 'text-input').value, '鳥');
  assert.equal(ui.requests.filter(r => r.url === '/api/convert-script').length, 1);
});

test('invalid/unavailable settings and custom paper are disclosed without retaining unrelated draft values', async t => {
  const bad = { ...complete, width: 9000, height: 'oops', font_size: -1, fit: 'false', spacing: -1,
    direction: 'diagonal', punctuation: 'keep', speed: 99, fps: 0, paper: '#ffffff', scale: 2, '<b>extra</b>': 3 };
  const ui = await createFrontend({ jobs: [makeJob('full', complete), makeJob('bad', bad, { style: 'removed-font' })] });
  t.after(ui.close);
  await reuse(ui, 'full');
  const theme = byId(ui, 'theme-select');
  theme.value = 'theme-rubbing';
  theme.dispatchEvent(new ui.window.Event('change'));
  await reuse(ui, 'bad');
  assert.equal(byId(ui, 'canvas-dim-val').textContent, '720 × 960');
  assertNumeric(ui, 'size-slider', 68);
  assertNumeric(ui, 'spacing-slider', 0.18);
  assertNumeric(ui, 'speed-select', 1);
  assertNumeric(ui, 'fps-select', 24);
  assert.equal(byId(ui, 'style-select').value, 'kai');
  assert.equal(byId(ui, 'fit-toggle').checked, true);
  assert.equal(byId(ui, 'punctuation-select').value, 'omit');
  assert.equal(byId(ui, 'btn-vertical').getAttribute('aria-pressed'), 'true');
  const notice = byId(ui, 'history-reuse-notice');
  assert.match(notice.textContent, /removed-font.*目前不可用/);
  assert.match(notice.textContent, /無法套用.*paper.*scale.*<b>extra<\/b>/);
  assert.equal(notice.querySelector('b'), null);
  assert.match(notice.textContent, /自訂紙墨顏色無法完整還原/);
  assert.equal(theme.value, 'theme-xuan');
  await reuse(ui, 'full');
  assert.equal(notice.hidden, true);
});

test('legacy gap, implicit appearance defaults and missing optional controls are handled truthfully', async t => {
  const params = { ...complete, gap: 0.36, paper: '#f8f3e9', ink: '#1c1b18', format: 'auto' };
  delete params.spacing;
  const ui = await createFrontend({ jobs: [makeJob('legacy', params)], setup(window) {
    window.document.getElementById('fit-toggle').remove();
    Object.defineProperty(window, 'localStorage', { get() { throw new Error('Storage blocked'); } });
  } });
  t.after(ui.close);
  await reuse(ui, 'legacy');
  assertNumeric(ui, 'spacing-slider', 0.36);
  assert.equal(byId(ui, 'history-reuse-notice').textContent, '適應畫布控制項不可用');
  assert.equal(byId(ui, 'btn-horizontal').getAttribute('aria-pressed'), 'true');
});

test('late metadata keeps a restored catalog font and never converts its saved text', async t => {
  let resolveStyles;
  let resolveCatalog;
  const ui = await createFrontend({ jobs: [makeJob('saved', complete, { text: '鸟', style: 'yan' })], fetch: ({ url }) => {
    if (url === '/api/styles') return new Promise(resolve => { resolveStyles = resolve; });
    if (url === '/api/font-catalog') return new Promise(resolve => { resolveCatalog = resolve; });
  } });
  t.after(ui.close);
  await reuse(ui, 'saved');
  assert.equal(byId(ui, 'style-select').value, 'yan');
  resolveStyles(jsonResponse({ styles: [{ id: 'kai', name: 'Kai' }] }));
  resolveCatalog(jsonResponse([]));
  await flush();
  assert.equal(byId(ui, 'style-select').value, 'yan');
  assert.equal(byId(ui, 'text-input').value, '鸟');
  assert.equal(ui.requests.some(r => r.url === '/api/convert-script'), false);
});

test('long supported canvases restore exactly and oversized areas use a disclosed safe default', async t => {
  const ui = await createFrontend({ jobs: [
    makeJob('long', { ...complete, width: 1280, height: 2400 }),
    makeJob('wide', { ...complete, width: 2400, height: 1280 }),
    makeJob('huge', { ...complete, width: 2400, height: 2400 }),
  ] });
  t.after(ui.close);
  await reuse(ui, 'long');
  assert.equal(byId(ui, 'canvas-dim-val').textContent, '1280 × 2400');
  assert.equal(byId(ui, 'history-reuse-notice').hidden, true);
  await reuse(ui, 'wide');
  assert.equal(byId(ui, 'canvas-dim-val').textContent, '2400 × 1280');
  assertNumeric(ui, 'canvas-len-slider', 2400);
  await reuse(ui, 'huge');
  assert.equal(byId(ui, 'canvas-dim-val').textContent, '720 × 960');
  assert.match(byId(ui, 'history-reuse-notice').textContent, /超出目前支援面積/);
});

test('reuse restores dark artwork and legacy light artwork instead of the current draft palette', async t => {
  const ui = await createFrontend({jobs: [makeJob('dark', {...complete, palette: 'dark'}), makeJob('old', complete)], fetch: exportResponse});
  t.after(ui.close);
  for (const [id, palette, theme] of [['dark', 'dark', 'theme-rubbing'], ['old', 'light', 'theme-xuan']]) {
    await reuse(ui, id);
    assert.equal(byId(ui, 'theme-select').value, theme);
    assert.equal(byId(ui, 'history-reuse-notice').hidden, true);
    await ui.tickTimeouts(800);
    byId(ui, 'btn-preview').click(); await flush();
    byId(ui, 'btn-render').click(); await flush();
    for (const url of ['/api/editor-preview', '/api/previews', '/api/renders']) {
      assert.equal(ui.requests.filter(r => r.url === url).at(-1).body.palette, palette, url);
    }
    byId(ui, 'creation-notice').querySelector('[data-close]').click();
    ui.window.location.hash = '#history';
    ui.window.dispatchEvent(new ui.window.HashChangeEvent('hashchange'));
    await flush();
  }
});
