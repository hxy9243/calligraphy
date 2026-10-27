import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const script = readFileSync(new URL('../frontend/analytics.js', import.meta.url), 'utf8');

async function load(t, fetch) {
  const dom = new JSDOM('<!doctype html><head></head><body></body>', {
    url: 'https://example.com/?private=secret#create',
    referrer: 'https://example.org/?token=secret#private',
    runScripts: 'outside-only',
  });
  t.after(() => dom.window.close());
  dom.window.fetch = fetch;
  await dom.window.eval(script);
  return dom.window;
}

test('analytics initializes the configured tag without incoming query or fragment data', async t => {
  const window = await load(t, async url => {
    assert.equal(url, '/api/analytics-config');
    return { ok: true, json: async () => ({ measurement_id: 'G-TEST123' }) };
  });
  const tag = window.document.querySelector('script');
  assert.equal(tag.src, 'https://www.googletagmanager.com/gtag/js?id=G-TEST123');
  assert.equal(tag.async, true);
  assert.equal(tag.referrerPolicy, 'no-referrer');
  const [command, id, config] = window.dataLayer[1];
  assert.equal(command, 'config');
  assert.equal(id, 'G-TEST123');
  assert.equal(config.page_location, 'https://example.com/');
  assert.equal(config.page_referrer, 'https://example.org/');
});

test('disabled, invalid, and unavailable configuration load no Google tag', async t => {
  for (const fetch of [
    async () => ({ ok: true, json: async () => ({ measurement_id: null }) }),
    async () => ({ ok: true, json: async () => ({ measurement_id: 'bad&injected=1' }) }),
    async () => ({ ok: false }),
    async () => { throw new Error('offline'); },
  ]) {
    const window = await load(t, fetch);
    assert.equal(window.document.querySelector('script'), null);
    assert.equal(window.gtag, undefined);
  }
});

test('only the workbench includes analytics, never capability-link viewers', () => {
  for (const name of ['index', 'watch', 'export']) {
    const html = readFileSync(new URL(`../frontend/${name}.html`, import.meta.url), 'utf8');
    assert.equal(html.includes('src="/analytics.js"'), name === 'index');
  }
});
