import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const key = 'calligraphy.preferences';
const styles = [{ id: 'kai', name: 'Kai' }, { id: 'yan', name: 'Yan' }];
const catalog = [
  { id: 'tw-sung', name_zh: '全字庫正宋體', char_support: 'trad' },
  { id: 'longcang-xingshu', name_zh: '龍藏行書', char_support: 'simp' },
].map(font => ({ name_en: font.id, style_category: 'kaishu', style_display: '書法',
  artist: '書家', dynasty_era: '當代', medium: 'brush', is_downloaded: 1, ...font }));
const byId = (ui, id) => ui.document.getElementById(id);
const stored = ui => JSON.parse(ui.window.localStorage.getItem(key));
function seed(value, extra) {
  return window => { window.localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value)); extra?.(window); };
}
function fetchFixture({ url }) {
  if (url === '/api/styles') return jsonResponse({ styles });
  if (url === '/api/font-catalog') return jsonResponse(catalog);
  if (url === '/api/previews') return jsonResponse({ preview_url: '/fixtures/preview.png' });
  if (url === '/api/renders') return jsonResponse({ job_id: 'preference-render', status: 'queued' }, 202);
}
function change(ui, id, value) {
  const control = byId(ui, id);
  control.value = value;
  control.dispatchEvent(new ui.window.Event('change'));
}
function pick(ui, id) {
  byId(ui, 'font-current').click();
  const item = [...ui.document.querySelectorAll('.picker-item')].find(item =>
    item.querySelector('img').getAttribute('src') === `/api/font-samples/${id}`);
  assert.ok(item, `font ${id} is offered`);
  item.click();
}
async function route(ui, view) {
  ui.document.querySelector(`[data-nav="${view}"]`).click();
  await flush();
}
function assertChoices(ui, style, theme) {
  assert.equal(byId(ui, 'style-select').value, style);
  assert.equal(byId(ui, 'theme-select').value, theme);
  assert.equal(ui.document.body.classList.contains(theme), true);
}

async function assertExportStyle(ui, style) {
  await ui.tickTimeouts(800);
  byId(ui, 'btn-preview').click();
  await flush();
  byId(ui, 'btn-render').click();
  await flush();
  for (const url of ['/api/editor-preview', '/api/previews', '/api/renders']) {
    assert.equal(ui.requests.filter(request => request.url === url).at(-1).body.style, style, url);
  }
}

test('font/style and paper theme survive panels and reload without persisting draft or capabilities', async t => {
  const ui = await createFrontend({ fetch: fetchFixture });
  t.after(ui.close);
  pick(ui, 'tw-sung');
  change(ui, 'theme-select', 'theme-rubbing');
  byId(ui, 'text-input').value = '私密草稿';
  byId(ui, 'text-input').dispatchEvent(new ui.window.Event('input'));
  ui.window.sessionStorage.setItem('fixture-share-capability', 'secret-token');
  for (const view of ['history', 'fonts', 'create']) {
    await route(ui, view);
    assertChoices(ui, 'tw-sung', 'theme-rubbing');
    assert.equal(byId(ui, 'text-input').value, '私密草稿');
  }
  await assertExportStyle(ui, 'tw-sung');
  assert.deepEqual(stored(ui), { version: 1, style: 'tw-sung', theme: 'theme-rubbing' });
  const snapshot = ui.window.localStorage.getItem(key);
  assert.doesNotMatch(snapshot, /私密|secret-token/);
  const reloaded = await createFrontend({ fetch: fetchFixture, setup: seed(snapshot) });
  t.after(reloaded.close);
  assertChoices(reloaded, 'tw-sung', 'theme-rubbing');
  assert.equal(byId(reloaded, 'font-current-name').textContent, '全字庫正宋體');
  assert.equal(byId(reloaded, 'text-input').value, '明月松間照\n清泉石上流');
  assert.equal(reloaded.window.sessionStorage.length, 0);
  await assertExportStyle(reloaded, 'tw-sung');
  change(reloaded, 'theme-select', 'theme-gold');
  pick(reloaded, 'yan');
  assertChoices(reloaded, 'yan', 'theme-gold');
  assert.deepEqual(stored(reloaded), { version: 1, style: 'yan', theme: 'theme-gold' });
});

for (const first of ['styles', 'catalog']) {
  test(`saved alias survives ${first}-first hydration and never converts current text`, async t => {
    const resolve = {};
    const ui = await createFrontend({ setup: seed({ version: 1, style: 'longcang', theme: 'theme-gold' }), fetch: ({ url }) => {
      if (url === '/api/styles') return new Promise(done => { resolve.styles = done; });
      if (url === '/api/font-catalog') return new Promise(done => { resolve.catalog = done; });
    } });
    t.after(ui.close);
    byId(ui, 'text-input').value = '保留繁體鳥';
    const responses = { styles: jsonResponse({ styles }), catalog: jsonResponse(catalog) };
    resolve[first](responses[first]);
    await flush();
    assert.equal(stored(ui).style, 'longcang');
    change(ui, 'theme-select', 'theme-rubbing');
    assert.equal(stored(ui).style, 'longcang', 'theme update must not save temporary Kai');
    await route(ui, 'history');
    await route(ui, 'create');
    const second = first === 'styles' ? 'catalog' : 'styles';
    resolve[second](responses[second]);
    await flush();
    assertChoices(ui, 'longcang', 'theme-rubbing');
    assert.equal(byId(ui, 'font-current-name').textContent, '龍藏行書');
    assert.equal(byId(ui, 'text-input').value, '保留繁體鳥');
    assert.equal(ui.requests.some(request => request.url === '/api/convert-script'), false);
  });
}

test('a newer explicit style selection wins over late saved-font metadata', async t => {
  let resolveCatalog;
  const ui = await createFrontend({ setup: seed({ version: 1, style: 'tw-sung' }), fetch: request => {
    if (request.url === '/api/font-catalog') return new Promise(resolve => { resolveCatalog = resolve; });
    return fetchFixture(request);
  } });
  t.after(ui.close);
  assert.equal(byId(ui, 'style-select').value, 'kai');
  change(ui, 'style-select', 'yan');
  resolveCatalog(jsonResponse(catalog));
  await flush();
  assertChoices(ui, 'yan', 'theme-xuan');
  assert.equal(stored(ui).style, 'yan');
});

test('catalog, recent-chip and history reuse choices update the same font preference', async t => {
  const ui = await createFrontend({ fetch: fetchFixture, jobs: [{ job_id: 'saved', job_type: 'render',
    status: 'succeeded', style: 'tw-sung', text: '舊作品', params: {} }] });
  t.after(ui.close);
  change(ui, 'theme-select', 'theme-gold');
  ui.document.querySelector('[data-font-id="tw-sung"] .btn-use').click();
  await flush();
  assert.equal(stored(ui).style, 'tw-sung');
  byId(ui, 'font-recent').querySelectorAll('button')[1].click();
  assert.equal(stored(ui).style, 'kai');
  ui.document.querySelector('[data-job-id="saved"] .job-text').click();
  byId(ui, 'detail-reuse').click();
  await flush();
  assertChoices(ui, 'tw-sung', 'theme-gold');
  assert.equal(stored(ui).style, 'tw-sung');
  assert.equal(byId(ui, 'text-input').value, '舊作品');
  assert.doesNotMatch(ui.window.localStorage.getItem(key), /舊作品/);
});

test('removed fonts fall back only after both successful lists arrive', async t => {
  let resolveCatalog;
  const ui = await createFrontend({ setup: seed({ version: 1, style: 'removed-font', theme: 'theme-rubbing' }), fetch: request => {
    if (request.url === '/api/font-catalog') return new Promise(resolve => { resolveCatalog = resolve; });
    return fetchFixture(request);
  } });
  t.after(ui.close);
  assert.equal(stored(ui).style, 'removed-font');
  resolveCatalog(jsonResponse(catalog));
  await flush();
  assertChoices(ui, 'kai', 'theme-rubbing');
  assert.equal(stored(ui).style, 'kai');
});

for (const failed of ['/api/styles', '/api/font-catalog']) {
  test(`failed ${failed} does not erase an unverified saved font`, async t => {
    const ui = await createFrontend({ setup: seed({ version: 1, style: 'unavailable-until-retry', theme: 'theme-gold' }), fetch: request => {
      if (request.url === failed) return jsonResponse({ error: 'temporary' }, 503);
      return fetchFixture(request);
    } });
    t.after(ui.close);
    assert.equal(stored(ui).style, 'unavailable-until-retry');
    change(ui, 'theme-select', 'theme-rubbing');
    assert.equal(stored(ui).style, 'unavailable-until-retry');
    assert.equal(stored(ui).theme, 'theme-rubbing');
  });
}

for (const value of ['{broken json', 'null', '[]', 'true', '{"version":2,"style":"yan","theme":"theme-gold"}',
  '{"version":1,"style":{},"theme":"theme-rubbing other-class"}']) {
  test(`invalid stored preferences ${value} safely retain defaults`, async t => {
    const ui = await createFrontend({ fetch: fetchFixture, setup: seed(value) });
    t.after(ui.close);
    assertChoices(ui, 'kai', 'theme-xuan');
    change(ui, 'theme-select', 'theme-gold');
    assert.deepEqual(stored(ui), { version: 1, theme: 'theme-gold' });
  });
}

test('valid fields survive individually and unknown data is never carried into preferences', async t => {
  const ui = await createFrontend({ fetch: fetchFixture, setup: seed({ version: 1, style: 'yan',
    theme: 'invalid', text: 'private draft', token: 'bearer', auth: 'private auth' }) });
  t.after(ui.close);
  assertChoices(ui, 'yan', 'theme-xuan');
  assert.deepEqual(stored(ui), { version: 1, style: 'yan' });
});

for (const mode of ['read', 'write']) {
  test(`blocked storage ${mode}s leave font and theme usable through panel changes`, async t => {
    const ui = await createFrontend({ fetch: fetchFixture, setup(window) {
      if (mode === 'read') Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked'); } });
      else window.Storage.prototype.setItem = () => { throw new Error('quota exceeded'); };
    } });
    t.after(ui.close);
    pick(ui, 'tw-sung');
    change(ui, 'theme-select', 'theme-rubbing');
    for (const view of ['history', 'fonts', 'create']) await route(ui, view);
    assertChoices(ui, 'tw-sung', 'theme-rubbing');
    await assertExportStyle(ui, 'tw-sung');
  });
}

test('font preferences coexist with saved direction, favorites and unrelated body classes', async t => {
  const ui = await createFrontend({ fetch: fetchFixture, setup: seed({ version: 1, style: 'yan', theme: 'theme-rubbing' }, window => {
    window.localStorage.setItem('calligraphy.direction', 'horizontal-lr');
    window.localStorage.setItem('calligraphy.favorites', JSON.stringify(['tw-sung']));
    window.document.body.classList.add('unrelated');
  }) });
  t.after(ui.close);
  assertChoices(ui, 'yan', 'theme-rubbing');
  assert.equal(byId(ui, 'btn-horizontal').getAttribute('aria-pressed'), 'true');
  assert.deepEqual(JSON.parse(ui.window.localStorage.getItem('calligraphy.favorites')), ['tw-sung']);
  change(ui, 'theme-select', 'theme-gold');
  assert.equal(ui.document.body.classList.contains('unrelated'), true);
});
