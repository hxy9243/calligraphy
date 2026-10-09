import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const catalog = JSON.parse(await readFile(new URL('../data/calligraphy_fonts.json', import.meta.url), 'utf8'))
  .filter(font => ['mashanzheng-kai', 'longcang-xingshu', 'lxgw-wenkai-tc'].includes(font.id))
  .map(({ file_path, source_url, ...metadata }) => metadata);

test('mobile viewport changes keep the rendered preview visible without requesting new pixels', async t => {
  let viewportWidth = 320;
  const ui = await createFrontend({ setup(window) {
    Object.defineProperty(window.document.getElementById('stage-viewport'), 'clientWidth', {
      get: () => viewportWidth,
    });
    window.innerWidth = 390;
    window.innerHeight = 700;
  } });
  t.after(ui.close);
  await ui.tickTimeouts(800);
  const preview = ui.document.getElementById('editor-preview');
  const status = ui.document.getElementById('editor-preview-status');
  const source = preview.src;
  const count = ui.requests.filter(r => r.url === '/api/editor-preview').length;
  assert.equal(preview.hidden, false);
  for (const height of [740, 760, 700]) {
    ui.window.innerHeight = height;
    ui.window.dispatchEvent(new ui.window.Event('scroll'));
    ui.window.dispatchEvent(new ui.window.Event('resize'));
    await ui.tickTimeouts(100);
    assert.equal(preview.hidden, false, 'address-bar resize must not blank the artwork');
    assert.equal(status.hidden, true);
  }
  const paper = ui.document.getElementById('calligraphy-stage');
  const previousWidth = paper.style.width;
  viewportWidth = 280;
  ui.window.innerWidth = 350;
  ui.window.dispatchEvent(new ui.window.Event('resize'));
  await ui.tickTimeouts(100);
  assert.notEqual(paper.style.width, previousWidth, 'real width changes still adjust the paper');
  assert.equal(preview.src, source);
  assert.equal(preview.hidden, false);
  await ui.tickTimeouts(800);
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').length, count);
  ui.document.getElementById('text-input').value = '永';
  ui.document.getElementById('text-input').dispatchEvent(new ui.window.Event('input'));
  await ui.tickTimeouts(800);
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body.text, '永');
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').length, count + 1);
});

test('scroll-related resizing does not invalidate an editor preview already in flight', async t => {
  let release;
  const ui = await createFrontend({ fetch({ url }) {
    if (url === '/api/editor-preview') return new Promise(resolve => { release = resolve; });
  } });
  t.after(ui.close);
  const pending = ui.tickTimeouts(800);
  await flush();
  for (let i = 0; i < 3; i++) {
    ui.window.innerHeight += 20;
    ui.window.dispatchEvent(new ui.window.Event('resize'));
    await ui.tickTimeouts(100);
  }
  release({ ok: true, blob: async () => new ui.window.Blob(['current']) });
  await pending;
  assert.equal(ui.document.getElementById('editor-preview').hidden, false);
  assert.equal(ui.document.getElementById('editor-preview-status').hidden, true);
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').length, 1);
});

test('the public picker uses raster samples and never offers unavailable built-in styles', async t => {
  const ui = await createFrontend({
    setup(window) {
      window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
      window.HTMLDialogElement.prototype.close = function () { this.open = false; };
    },
    fetch({ url }) {
      if (url === '/api/styles') return jsonResponse({ styles: [
        { id: 'kai', name: 'Kai' }, { id: 'yan', name: 'Yan' },
        { id: 'mashanzheng', name: 'Ma Shan Zheng' },
        { id: 'longcang', name: 'Long Cang' },
        { id: 'lxgw-wenkai-tc', name: 'WenKai TC' },
      ] });
      if (url === '/api/font-catalog') return jsonResponse(catalog);
    },
  });
  t.after(ui.close);
  const { document } = ui;
  assert.equal(document.querySelector('[data-font-id="aa shoujin"]'), null);
  document.querySelector('[data-filter="support"] [data-val="all"]').click();
  assert.equal(document.querySelectorAll('.font-card').length, 5);
  const images = document.querySelectorAll('.glyph-sample img');
  assert.equal(images.length, 5);
  for (const image of images) assert.match(image.getAttribute('src'), /^\/api\/font-samples\//);
  assert.equal(document.getElementById('dynamic-font-faces'), null);
  assert.equal(document.querySelector('link[href*="fonts.googleapis.com"]'), null);

  document.querySelector('[data-font-id="mashanzheng-kai"] .btn-use').click();
  await flush();
  assert.equal(document.getElementById('style-select').value, 'mashanzheng');
  assert.equal(document.querySelector('#font-current-glyph img').getAttribute('src'), '/api/font-samples/mashanzheng-kai');
  document.getElementById('font-current').click();
  document.querySelector('#picker-support [data-sup="all"]').click();
  assert.equal(document.querySelectorAll('.picker-sample img').length, 5);
  assert.equal(document.querySelectorAll('.picker-item').length, 5);
  assert.ok(ui.requests.every(request => !request.url.startsWith('/fonts/')));
});

test('the editor requests raster previews after edits and ignores obsolete responses', async t => {
  let release;
  const ui = await createFrontend({ fetch({ url }) {
    if (url === '/api/editor-preview') return new Promise(resolve => { release = resolve; });
  } });
  t.after(ui.close);
  const { document, window } = ui;
  const input = document.getElementById('text-input');
  input.value = '永';
  input.dispatchEvent(new window.Event('input'));
  const firstTick = ui.tickTimeouts();
  await flush();
  const first = ui.requests.find(r => r.url === '/api/editor-preview');
  assert.equal(first.body.text, '永');
  assert.equal(first.body.direction, 'vertical-rl');
  assert.ok(first.body.width <= 640 && first.body.height <= 640);
  input.value = '明月';
  input.dispatchEvent(new window.Event('input'));
  release({ ok: true, blob: async () => new window.Blob(['old']) });
  await firstTick;
  await flush();
  assert.equal(document.getElementById('editor-preview').hidden, true);
  const secondTick = ui.tickTimeouts();
  await flush();
  release({ ok: true, blob: async () => new window.Blob(['new']) });
  await secondTick;
  await flush();
  assert.equal(document.getElementById('editor-preview').hidden, false);
  assert.equal(document.getElementById('editor-preview-status').hidden, true);
  assert.ok(ui.requests.every(r => !['/api/previews', '/api/renders'].includes(r.url)));
  const star = document.querySelector('.github-star');
  assert.equal(star.href, 'https://github.com/hxy9243/calligraphy');
  assert.equal(star.target, '_blank');
  assert.match(star.rel, /noopener/);
  assert.equal(document.getElementById('calligraphy-stage').contains(document.getElementById('editor-preview-status')), false);
});

test('first visits use traditional text and presets, and backend missing-glyph warnings block exports', async t => {
  const ui = await createFrontend({ fetch({ url, body }) {
    if (url === '/api/editor-preview' && body.text === '龘') {
      return jsonResponse({ detail: 'Missing font glyphs: 龘' }, 422);
    }
  } });
  t.after(ui.close);
  const { document, window } = ui;
  const input = document.getElementById('text-input');
  assert.equal(input.value, '明月松間照\n清泉石上流');
  assert.ok(document.getElementById('btn-trad').classList.contains('active'));
  document.querySelector('[data-preset="chunxiao"]')?.click();
  const spring = [...document.querySelectorAll('.preset-btn')].find(button => button.textContent.includes('春曉'));
  assert.ok(spring);
  spring.click();
  assert.match(input.value, /春眠不覺曉/);
  input.value = '龘';
  input.dispatchEvent(new window.Event('input'));
  await ui.tickTimeouts();
  const warning = document.getElementById('font-glyph-warning');
  assert.equal(warning.hidden, false);
  assert.match(warning.textContent, /龘/);
  document.getElementById('btn-preview').click();
  document.getElementById('btn-render').click();
  await flush();
  assert.ok(ui.requests.every(r => !['/api/previews', '/api/renders'].includes(r.url)));
  input.value = '永';
  input.dispatchEvent(new window.Event('input'));
  await ui.tickTimeouts();
  assert.equal(warning.hidden, true);
  assert.equal(document.getElementById('editor-preview').hidden, false);
});

test('a delayed missing-glyph response cannot warn about newer text', async t => {
  let release;
  const ui = await createFrontend({ fetch({ url, body }) {
    if (url === '/api/editor-preview' && body.text === '龘') {
      return { ok: false, status: 422, json: () => new Promise(resolve => { release = resolve; }) };
    }
  } });
  t.after(ui.close);
  const input = ui.document.getElementById('text-input');
  input.value = '龘';
  input.dispatchEvent(new ui.window.Event('input'));
  const pending = ui.tickTimeouts();
  await flush();
  input.value = '永';
  input.dispatchEvent(new ui.window.Event('input'));
  release({ detail: 'Missing font glyphs: 龘' });
  await pending;
  await ui.tickTimeouts();
  assert.equal(ui.document.getElementById('font-glyph-warning').hidden, true);
  assert.equal(ui.document.getElementById('editor-preview').hidden, false);
});
