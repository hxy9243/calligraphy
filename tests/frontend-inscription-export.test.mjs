import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

test('still and video preserve default, custom multiline and cleared inscriptions', async t => {
  const ui = await createFrontend({ fetch: ({ url }) => {
    if (url === '/api/previews') return jsonResponse({ preview_url: '/fixture.png' });
    if (url === '/api/renders') return jsonResponse({ job_id: 'fixture' }, 202);
  } });
  t.after(ui.close);
  const input = ui.document.getElementById('inscription-input');
  assert.ok(input.value.trim(), 'the date-based default inscription is populated');
  for (const value of [input.value, '清風\n明月', '']) {
    input.value = value;
    input.dispatchEvent(new ui.window.Event('input'));
    for (const [button, endpoint] of [['btn-preview', '/api/previews'], ['btn-render', '/api/renders']]) {
      ui.document.getElementById(button).click();
      await flush();
      const request = ui.requests.filter(r => r.url === endpoint).at(-1);
      assert.equal(request.body.inscription, value.trim() || undefined);
    }
  }
});
