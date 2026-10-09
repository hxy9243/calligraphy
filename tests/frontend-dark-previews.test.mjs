import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const css = await readFile(new URL('../frontend/style.css', import.meta.url), 'utf8');
const artworkSelectors = ['.font-current-glyph', '.picker-sample', '.glyph-sample',
  '.stage-paper', '.viewer', '.export-output-box', '.job-thumb', '#detail-viewer'];

function luminance(hex) {
  const channels = hex.match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16) / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
  return channels.reduce((sum, value, i) => sum + value * [.2126, .7152, .0722][i], 0);
}
const contrast = (light, dark) => (luminance(light) + .05) / (luminance(dark) + .05);

test('dark artwork surfaces use light paper with readable dark ink, not dark UI paper', () => {
  // CSS contract, not a browser rasterization test. Match actual selector rules
  // because jsdom does not resolve custom properties or implement layout.
  const dom = new JSDOM(`<style>${css}</style>`);
  const rules = [...dom.window.document.styleSheets[0].cssRules];
  for (const selector of artworkSelectors) {
    const rule = rules.find(rule => rule.selectorText?.split(',').map(s => s.trim())
      .includes(`body.theme-rubbing ${selector}`));
    assert.ok(rule, `${selector} has an explicit dark-theme artwork surface`);
    assert.equal(rule.style.background, '#faf7f0');
    assert.ok(contrast(rule.style.background, '#1c1b18') >= 12, `${selector} source-font ink contrast`);
    assert.ok(contrast(rule.style.background, rule.style.color) >= 12, `${selector} fallback text contrast`);
    assert.equal(rule.style.getPropertyValue('filter'), '');
    assert.equal(rule.style.getPropertyValue('opacity'), '');
    assert.equal(rule.style.getPropertyValue('mix-blend-mode'), '');
  }
  const theme = rules.find(rule => rule.selectorText === 'body.theme-rubbing');
  assert.equal(theme.style.getPropertyValue('--paper'), '#141414', 'non-artwork UI keeps dark paper');
  assert.equal(theme.style.getPropertyValue('--surface'), '#242424');
  const placeholder = rules.find(rule => rule.selectorText === 'body.theme-rubbing .job-thumb .placeholder');
  assert.ok(contrast('#faf7f0', placeholder.style.color) >= 4.5);
  dom.window.close();
});

test('switching themes repeatedly preserves preview URLs, inline artwork and download targets', async t => {
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><path fill="#1c1b18" d="M10 10h40v60H10z"/></svg>';
  const ui = await createFrontend({ fetch: ({ url }) => url === '/api/previews' ? jsonResponse({ svg }) : undefined });
  t.after(ui.close);
  await ui.tickTimeouts(800);
  ui.document.getElementById('btn-preview').click();
  await flush();
  await ui.tickTimeouts(800);
  const image = ui.document.getElementById('editor-preview');
  const source = image.src;
  const artwork = ui.document.querySelector('#preview-svg-container svg');
  const original = artwork.outerHTML;
  const download = ui.document.getElementById('result-download').href;
  const pixelRequests = () => ui.requests.filter(r => ['/api/editor-preview', '/api/previews', '/api/renders'].includes(r.url)).length;
  const requests = pixelRequests();
  const theme = ui.document.getElementById('theme-select');
  for (const value of ['theme-rubbing', 'theme-gold', 'theme-xuan', 'theme-rubbing']) {
    theme.value = value;
    theme.dispatchEvent(new ui.window.Event('change'));
    await ui.tickTimeouts(800);
    assert.ok(ui.document.body.classList.contains(value));
    assert.equal(image.src, source);
    assert.equal(image.hidden, false);
    assert.equal(ui.document.querySelector('#preview-svg-container svg'), artwork);
    assert.equal(artwork.outerHTML, original);
    assert.equal(ui.document.getElementById('result-download').href, download);
    assert.equal(pixelRequests(), requests, 'theme is display-only');
  }
});
