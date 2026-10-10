import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const endpoints = ['/api/editor-preview', '/api/previews', '/api/renders'];
const keys = ['width', 'height', 'font_size', 'fit', 'spacing', 'direction', 'punctuation'];

for (const direction of ['vertical-rl', 'horizontal-lr']) {
  test(`${direction}: editor, still and video submit one logical composition`, async t => {
    const ui = await createFrontend({ fetch: ({ url }) => {
      if (url === '/api/previews') return jsonResponse({ preview_url: '/test.png' });
      if (url === '/api/renders') return jsonResponse({ job_id: 'vid_composition', status: 'queued' }, 202);
    } });
    t.after(ui.close);
    const { document, window } = ui;
    document.getElementById(direction === 'vertical-rl' ? 'btn-vertical' : 'btn-horizontal').click();
    document.querySelector('[data-cf="9:16"]').click();
    const set = (id, value) => {
      const element = document.getElementById(id);
      element.value = value;
      element.dispatchEvent(new window.Event('input', { bubbles: true }));
    };
    set('size-slider', '110');
    set('spacing-slider', '0.4');
    document.getElementById('fit-toggle').checked = false;
    document.getElementById('fit-toggle').dispatchEvent(new window.Event('change', { bubbles: true }));
    await ui.tickTimeouts(800);
    document.getElementById('btn-preview').click(); await flush();
    document.getElementById('btn-render').click(); await flush();
    const bodies = endpoints.map(url => ui.requests.filter(r => r.url === url).at(-1)?.body);
    for (const body of bodies) {
      assert.ok(body);
      assert.equal(body.font_size, 110);
      assert.equal(body.fit, false);
      assert.equal(body.spacing, 0.4);
      assert.equal(body.width, 720);
      assert.equal(body.height, 1280);
      assert.equal(body.direction, direction);
    }
    const composition = body => Object.fromEntries(keys.map(key => [key, body[key]]));
    assert.deepEqual(composition(bodies[0]), composition(bodies[1]));
    assert.deepEqual(composition(bodies[0]), composition(bodies[2]));
  });
}

test('auto canvas dimensions above 1280 are preserved in all export payloads', async t => {
  const ui = await createFrontend({ fetch: ({ url }) => {
    if (url === '/api/previews') return jsonResponse({ preview_url: '/test.png' });
    if (url === '/api/renders') return jsonResponse({ job_id: 'vid_long', status: 'queued' }, 202);
  } });
  t.after(ui.close);
  ui.document.getElementById('text-input').value = '永'.repeat(20);
  ui.document.getElementById('text-input').dispatchEvent(new ui.window.Event('input', { bubbles: true }));
  await ui.tickTimeouts(800);
  ui.document.getElementById('btn-preview').click(); await flush();
  ui.document.getElementById('btn-render').click(); await flush();
  const bodies = endpoints.map(url => ui.requests.filter(r => r.url === url).at(-1)?.body);
  assert.equal(bodies[0].height, 2200);
  for (const body of bodies) {
    assert.equal(body.width, bodies[0].width);
    assert.equal(body.height, 2200);
  }
});
