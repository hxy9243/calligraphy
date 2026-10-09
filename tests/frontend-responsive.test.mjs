import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

const css = await readFile(new URL('../frontend/style.css', import.meta.url), 'utf8');

// CSS contract checks, not a substitute for browser layout measurements.
function createLayoutAt(width) {
  const dom = new JSDOM(`<style>${css}</style>`);
  const result = {};
  function visit(rules) {
    for (const rule of rules) {
      if (rule.media) {
        const query = rule.media.mediaText;
        const match = /^\((min|max)-width:\s*(\d+)px\)$/.exec(query);
        if (match && (match[1] === 'min' ? width >= +match[2] : width <= +match[2])) visit(rule.cssRules);
      } else if (rule.selectorText === '.create-grid') {
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
  for (const width of [320, 375, 390, 414, 640, 768, 960]) {
    const layout = createLayoutAt(width);
    assert.equal(layout.display, 'flex', `${width}px`);
    assert.equal(layout['flex-direction'], 'column', `${width}px`);
    assert.equal(layout['align-items'], 'stretch', `${width}px`);
  }
  const desktop = createLayoutAt(1280);
  assert.equal(desktop.display, 'grid');
  assert.equal(desktop['grid-template-columns'], 'minmax(340px, 400px) 1fr');
});
