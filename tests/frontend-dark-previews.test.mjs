import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const css = await readFile(new URL('../frontend/style.css', import.meta.url), 'utf8');
const changeTheme = (ui, value) => {
  const theme = ui.document.getElementById('theme-select');
  theme.value = value;
  theme.dispatchEvent(new ui.window.Event('change'));
};
const endpoints = ['/api/editor-preview', '/api/previews', '/api/renders'];
const response = ({ url }) => {
  if (url === '/api/previews') return jsonResponse({ svg: '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#141414"/><path fill="#ffffff"/></svg>' });
  if (url === '/api/renders') return jsonResponse({ job_id: 'palette-render', status: 'queued' }, 202);
};

test('dark artwork surfaces match rendered paper while fixed font references stay legible', () => {
  const dom = new JSDOM(`<style>${css}</style>`);
  const rules = [...dom.window.document.styleSheets[0].cssRules];
  for (const [selectors, paper, ink] of [
    [['.font-current-glyph', '.picker-sample', '.glyph-sample'], '#faf7f0', '#1c1b18'],
    [['.stage-paper', '.viewer', '.export-output-box', '.job-thumb', '#detail-viewer'], '#141414', '#ffffff'],
  ]) {
    for (const selector of selectors) {
      const rule = rules.find(rule => rule.selectorText?.split(',').map(s => s.trim()).includes(`body.theme-rubbing ${selector}`));
      assert.ok(rule, selector);
      assert.equal(rule.style.background, paper);
      assert.equal(rule.style.color, ink);
      for (const property of ['filter', 'opacity', 'mix-blend-mode']) assert.equal(rule.style.getPropertyValue(property), '');
    }
  }
  dom.window.close();
});

for (const style of ['kai', 'yan', 'tw-sung']) {
  test(`${style}: dark selection and reload submit the same palette for editor, still and video`, async t => {
    const ui = await createFrontend({ fetch: response, setup(window) {
      window.localStorage.setItem('calligraphy.preferences', JSON.stringify({version: 1, theme: 'theme-rubbing'}));
    } });
    t.after(ui.close);
    const select = ui.document.getElementById('style-select');
    select.add(new ui.window.Option(style, style)); select.value = style;
    select.dispatchEvent(new ui.window.Event('change'));
    await ui.tickTimeouts(800);
    ui.document.getElementById('btn-preview').click(); await flush();
    ui.document.getElementById('btn-render').click(); await flush();
    for (const url of endpoints) {
      const body = ui.requests.filter(r => r.url === url).at(-1).body;
      assert.equal(body.palette, 'dark', url);
      assert.equal(body.style, style, url);
    }
    const artwork = ui.document.querySelector('#preview-svg-container svg');
    const original = artwork.outerHTML;
    const download = ui.document.getElementById('result-download').href;
    for (const theme of ['theme-gold', 'theme-xuan', 'theme-rubbing']) {
      changeTheme(ui, theme);
      await ui.tickTimeouts(800);
      assert.equal(ui.requests.filter(r => r.url === endpoints[0]).at(-1).body.palette, theme === 'theme-rubbing' ? 'dark' : 'light');
      assert.equal(artwork.outerHTML, original, 'completed artwork is never recolored');
      assert.equal(ui.document.getElementById('result-download').href, download);
    }
  });
}

test('a late light response cannot replace the dark editor after switching backgrounds', async t => {
  let finishLight;
  const ui = await createFrontend({ fetch: ({url, body}) => {
    if (url === '/api/editor-preview' && body.palette === 'light') return new Promise(resolve => { finishLight = resolve; });
  } });
  t.after(ui.close);
  const pending = ui.tickTimeouts(800);
  await flush();
  assert.ok(finishLight);
  changeTheme(ui, 'theme-rubbing');
  const image = ui.document.getElementById('editor-preview');
  finishLight({ok: true, blob: async () => new ui.window.Blob(['old'])});
  await pending;
  assert.equal(image.hidden, true);
  await ui.tickTimeouts(800);
  assert.equal(ui.requests.filter(r => r.url === endpoints[0]).at(-1).body.palette, 'dark');
  assert.equal(image.hidden, false);
});
