import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';
import { createFrontend } from './helpers/frontend.mjs';

const css = await readFile(new URL('../frontend/style.css', import.meta.url), 'utf8');

// CSS contract checks, not a substitute for browser layout measurements.
function rulesAt(width, selector = '.create-grid') {
  const dom = new JSDOM(`<style>${css}</style>`);
  const result = {};
  function visit(rules) {
    for (const rule of rules) {
      if (rule.media) {
        const query = rule.media.mediaText;
        const match = /^\((min|max)-width:\s*(\d+)px\)$/.exec(query);
        if (match && (match[1] === 'min' ? width >= +match[2] : width <= +match[2])) visit(rule.cssRules);
      } else if (rule.selectorText?.split(',').map(value => value.trim()).includes(selector)) {
        for (let i = 0; i < rule.style.length; i++) {
          const property = rule.style[i];
          result[property] = rule.style.getPropertyValue(property);
        }
      }
    }
  }
  visit(dom.window.document.styleSheets[0].cssRules);
  dom.window.close();
  return result;
}

test('narrow create cards stretch so long font labels and recents cannot set their width', () => {
  for (const width of [320, 360, 375, 390, 414, 640, 768, 960]) {
    const layout = rulesAt(width);
    assert.equal(layout.display, 'flex', `${width}px`);
    assert.equal(layout['flex-direction'], 'column', `${width}px`);
    assert.equal(layout['align-items'], 'stretch', `${width}px`);
  }
  const desktop = rulesAt(1280);
  assert.equal(desktop.display, 'grid');
  assert.equal(desktop['grid-template-columns'], 'minmax(340px, 400px) minmax(0, 1fr)');
});

// These tests check the CSS contract only. JSDOM does not compute layout.
test('narrow cards have identical width bounds independently of intrinsic content', () => {
  for (const width of [320, 360, 375, 390, 414, 768, 960]) {
    for (const selector of ['.compose > .card', '.create-grid > .canvas']) {
      const layout = rulesAt(width, selector);
      assert.equal(layout.width, '100%', `${selector} at ${width}px`);
      assert.equal(layout['max-width'], '100%');
    }
    assert.equal(rulesAt(width, '.creation-note').order, '5', 'text stays first, usage note follows output');
  }
  assert.equal(rulesAt(1280, '.compose > .card').width, undefined);
});

test('mobile controls and grids shrink without clipping the page or picker', () => {
  for (const width of [320, 360, 375, 390, 414, 640]) {
    assert.equal(rulesAt(width, '.card').padding, rulesAt(width, '.canvas').padding);
    assert.equal(rulesAt(width, '.fonts-grid')['grid-template-columns'], 'minmax(0, 1fr)');
    assert.equal(rulesAt(width, '.history-grid')['grid-template-columns'], 'repeat(2, minmax(0, 1fr))');
    assert.equal(rulesAt(width, '.field-row')['grid-template-columns'], 'minmax(0, 1fr)');
    assert.equal(rulesAt(width, '.action-bar .btn')['min-width'], '0');
    assert.equal(rulesAt(width, '.action-bar').width, undefined, 'fixed action bar retains left/right insets');
    assert.equal(rulesAt(width, '.job-action')['flex-wrap'], 'wrap');
    assert.equal(rulesAt(width, '.search')['font-size'], '16px');
    for (const selector of ['textarea', '.search', 'select', '.font-current', '.chip-row']) {
      const control = rulesAt(width, selector);
      assert.equal(control['min-width'], '0');
      assert.equal(control['max-width'], '100%');
    }
    for (const selector of ['html', 'body']) {
      assert.equal(rulesAt(width, selector)['overflow-x'], undefined, 'do not hide unresolved page overflow');
    }
    assert.equal(rulesAt(width, '.chip-row.scroll')['overflow-x'], 'auto', 'chips retain intentional local scrolling');
    assert.equal(rulesAt(width, '.sheet-inner')['overflow-x'], undefined, 'do not clip dialogs');
  }
});

test('vertical paper fits the measured content box below 260px and keeps its aspect ratio', async t => {
  // Model the measured stage box; this is a sizing-logic test, not a layout engine.
  let clientWidth = 260;
  const ui = await createFrontend({ setup(window) {
    const viewport = window.document.getElementById('stage-viewport');
    viewport.style.padding = '14px';
    Object.defineProperty(viewport, 'clientWidth', { get: () => clientWidth });
  } });
  t.after(ui.close);
  await ui.tickTimeouts(800);
  const paper = ui.document.getElementById('calligraphy-stage');
  const preview = ui.document.getElementById('editor-preview');
  const source = preview.src;
  const requestCount = ui.requests.filter(request => request.url === '/api/editor-preview').length;
  for (const width of [320, 360, 375, 390, 414, 768]) {
    clientWidth = width - 52; // outer gutters, card padding/borders, stage borders
    ui.window.innerWidth = width;
    ui.window.dispatchEvent(new ui.window.Event('resize'));
    await ui.tickTimeouts(100);
    const available = clientWidth - 28;
    const paperWidth = parseFloat(paper.style.width);
    assert.ok(paperWidth <= available, `${width}px: ${paperWidth} <= ${available}`);
    assert.equal(parseFloat(paper.style.minWidth), paperWidth);
    assert.equal(parseFloat(paper.style.height), Math.round(paperWidth * 760 / 720));
    assert.equal(preview.src, source);
    assert.equal(preview.hidden, false);
  }
  await ui.tickTimeouts(800);
  assert.equal(ui.requests.filter(request => request.url === '/api/editor-preview').length, requestCount);
  clientWidth = 260;
  ui.document.getElementById('btn-horizontal').click();
  assert.ok(parseFloat(paper.style.width) > clientWidth - 28, 'wide horizontal artwork retains intentional local scrolling');
});
