import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

test('studio presets omit the Yong demo in both scripts and preserve the other examples', async t => {
  const ui = await createFrontend({ fetch({ url, body }) {
    if (url === '/api/convert-script') return jsonResponse({ text: body.text, target: body.target });
  } });
  t.after(ui.close);
  const { document } = ui;

  for (const toggle of [null, 'btn-simp', 'btn-trad']) {
    if (toggle) {
      document.getElementById(toggle).click();
      await flush();
    }
    const presets = [...document.querySelectorAll('#preset-list .preset-btn')];
    assert.equal(presets.length, 17);
    assert.ok(presets.every(button => !button.textContent.includes('永字八法')));
    const river = presets.find(button => button.textContent === '春江花月夜');
    assert.ok(river, 'the neighboring preset remains available');
    river.click();
    assert.equal(document.getElementById('text-input').value, '春江花月夜');
    assert.equal(document.getElementById('calligraphy-text').textContent, '春江花月夜');
  }
});

test('custom Yong text still reaches live preview, still export and video export', async t => {
  const ui = await createFrontend({ fetch({ url }) {
    if (url === '/api/previews') return jsonResponse({ preview_url: '/fixtures/yong.png' });
    if (url === '/api/renders') return jsonResponse({ job_id: 'custom-yong', status: 'queued' }, 202);
  } });
  t.after(ui.close);
  const input = ui.document.getElementById('text-input');
  input.value = '永';
  input.dispatchEvent(new ui.window.Event('input'));
  await ui.tickTimeouts(800);
  ui.document.getElementById('btn-preview').click();
  await flush();
  ui.document.getElementById('btn-render').click();
  await flush();

  for (const url of ['/api/editor-preview', '/api/previews', '/api/renders']) {
    const request = ui.requests.filter(request => request.url === url).at(-1);
    assert.ok(request, `${url} was requested`);
    assert.equal(request.body.text, '永');
  }
});
