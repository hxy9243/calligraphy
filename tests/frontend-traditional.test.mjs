import test from 'node:test';
import assert from 'node:assert/strict';
import * as OpenCC from 'opencc-js';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const catalog = [
  { id: 'traditional-kai', name_zh: '传统楷书', char_support: 'trad' },
  { id: 'simplified-kai', name_zh: '简体楷书', char_support: 'simp' },
  { id: 'both-kai', name_zh: '繁简楷书', char_support: 'both' },
].map(font => ({
  name_en: font.id, style_category: 'kaishu', style_display: '楷书',
  artist: '王书家', dynasty_era: '当代', font_author: '字体作者',
  aesthetic_notes: '书写流畅', license: '开源字体',
  medium: 'brush', is_downloaded: 1, ...font,
}));
const styles = [
  // API order must not select a Simplified-only font before the default Kai.
  { id: 'simplified-kai', name: '简体楷书', description: '简体书写' },
  { id: 'kai', name: '标准楷书', description: '拟合笔画书写' },
  { id: 'traditional-kai', name: '传统楷书', description: '传统书写' },
  { id: 'both-kai', name: '繁简楷书', description: '繁简书写' },
];

async function setup(t, configure) {
  const ui = await createFrontend({
    setup(window) {
      window.OpenCC = OpenCC;
      configure?.(window);
    },
    fetch({ url, body }) {
      if (url === '/api/styles') return jsonResponse({ styles });
      if (url === '/api/font-catalog') return jsonResponse(catalog);
      if (url === '/api/convert-script') {
        const convert = OpenCC.Converter({ from: body.target === 'trad' ? 'cn' : 't', to: body.target === 'trad' ? 't' : 'cn' });
        return jsonResponse({ text: convert(body.text), target: body.target });
      }
      if (url === '/api/previews') return jsonResponse({ preview_url: '/preview.png' });
      if (url === '/api/renders') return jsonResponse({ job_id: 'traditional-render' }, 202);
    },
  });
  t.after(ui.close);
  return ui;
}

test('fresh boot keeps Traditional text through preview and render with Kai selected', async t => {
  const ui = await setup(t);
  const { document } = ui;
  const initialText = '明月松間照\n清泉石上流';
  assert.equal(document.documentElement.lang, 'zh-Hant');
  assert.equal(document.getElementById('text-input').value, initialText);
  assert.equal(document.getElementById('style-select').value, 'kai');
  assert.equal(document.getElementById('font-current-name').textContent, '標準楷書');
  assert.equal(document.getElementById('btn-trad').getAttribute('aria-pressed'), 'true');
  assert.equal(document.getElementById('btn-simp').getAttribute('aria-pressed'), 'false');
  assert.equal(document.querySelector('.preset-btn').textContent, '王維聯句');
  assert.ok(ui.requests.every(request => request.url !== '/api/convert-script'));

  await ui.tickTimeouts(800);
  document.getElementById('btn-preview').click();
  await flush();
  document.getElementById('btn-render').click();
  await flush();
  for (const url of ['/api/editor-preview', '/api/previews', '/api/renders']) {
    const request = ui.requests.find(request => request.url === url);
    assert.ok(request, `${url} was requested`);
    assert.equal(request.body.text, initialText);
    assert.equal(request.body.style, 'kai');
  }
});

test('picker and catalogue default to Traditional-capable fonts with localized display names', async t => {
  const ui = await setup(t);
  const { document } = ui;
  assert.equal(document.querySelector('[data-filter="support"] .active').dataset.val, 'trad');
  assert.deepEqual([...document.querySelectorAll('.font-card')].map(card => card.dataset.fontId), ['kai', 'traditional-kai', 'both-kai']);
  assert.equal(document.querySelector('[data-font-id="traditional-kai"] h3').textContent, '傳統楷書');
  assert.match(document.querySelector('[data-font-id="traditional-kai"] .aesthetic').textContent, /書寫流暢/);
  assert.equal(document.querySelector('#style-select option[value="simplified-kai"]').textContent, '簡體楷書 - 簡體書寫');

  document.getElementById('font-current').click();
  assert.equal(document.querySelector('#picker-support .active').dataset.sup, 'trad');
  assert.deepEqual([...document.querySelectorAll('.picker-info strong')].map(name => name.textContent), ['標準楷書', '傳統楷書', '繁簡楷書']);
  assert.ok([...document.querySelectorAll('.picker-sample img')].some(image => image.getAttribute('src') === '/api/font-samples/traditional-kai'));
  assert.equal(catalog[0].name_zh, '传统楷书', 'localization must not mutate source metadata');
});

test('font search matches Simplified and Traditional queries against Traditional display labels', async t => {
  const ui = await setup(t);
  const { document, window } = ui;
  document.getElementById('font-current').click();
  for (const [id, results] of [['fonts-search', '.font-card h3'], ['picker-search', '.picker-info strong']]) {
    const input = document.getElementById(id);
    for (const query of ['传统', '傳統']) {
      input.value = query;
      input.dispatchEvent(new window.Event('input'));
      assert.deepEqual([...document.querySelectorAll(results)].map(name => name.textContent), ['傳統楷書']);
    }
  }
});

test('explicit Simplified conversion and font filters remain available', async t => {
  const ui = await setup(t);
  const { document } = ui;
  document.getElementById('btn-simp').click();
  await flush();
  assert.equal(document.getElementById('text-input').value, '明月松间照\n清泉石上流');
  assert.equal(document.querySelector('.preset-btn').textContent, '王维联句');
  assert.equal(document.getElementById('btn-simp').getAttribute('aria-pressed'), 'true');
  assert.equal(document.getElementById('btn-trad').getAttribute('aria-pressed'), 'false');

  document.querySelector('[data-filter="support"] [data-val="simp"]').click();
  assert.deepEqual([...document.querySelectorAll('.font-card')].map(card => card.dataset.fontId), ['kai', 'simplified-kai', 'both-kai']);
  document.getElementById('font-current').click();
  document.querySelector('#picker-support [data-sup="simp"]').click();
  await flush();
  const simplified = [...document.querySelectorAll('.picker-info strong')].find(name => name.textContent === '簡體楷書');
  assert.ok(simplified);
  simplified.closest('.picker-item').click();
  await flush();
  assert.equal(document.getElementById('style-select').value, 'simplified-kai');
  assert.equal(document.getElementById('font-current-name').textContent, '簡體楷書');
  assert.equal(document.getElementById('text-input').value, '明月松间照\n清泉石上流');
  document.getElementById('font-current').click();
  assert.equal(document.querySelector('#picker-support .active').dataset.sup, 'simp', 'reopening preserves explicit filter choice');
  document.querySelector('#picker-support [data-sup="all"]').click();
  assert.equal(document.querySelectorAll('.picker-item').length, 4);
});

test('Traditional defaults leave existing text and saved preferences alone', async t => {
  const savedFavorites = JSON.stringify(['simplified-kai']);
  const draft = '保留我的简体文本';
  const ui = await setup(t, window => {
    window.localStorage.setItem('calligraphy.direction', 'horizontal-lr');
    window.localStorage.setItem('calligraphy.favorites', savedFavorites);
    window.document.getElementById('text-input').value = draft;
  });
  const { document, window } = ui;
  document.getElementById('font-current').click();
  assert.equal(document.getElementById('text-input').value, draft);
  assert.equal(window.localStorage.getItem('calligraphy.direction'), 'horizontal-lr');
  assert.equal(window.localStorage.getItem('calligraphy.favorites'), savedFavorites);
  assert.ok(ui.requests.every(request => request.url !== '/api/convert-script'));
  document.querySelector('#picker-support [data-sup="all"]').click();
  document.querySelector('#picker-cats [data-cat="fav"]').click();
  assert.deepEqual([...document.querySelectorAll('.picker-info strong')].map(name => name.textContent), ['簡體楷書']);
});
