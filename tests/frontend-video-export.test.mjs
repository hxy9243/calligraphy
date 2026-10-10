import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const job = { job_id: 'vid_one', job_type: 'render', status: 'succeeded', text: '永', style: 'kai', created_at: new Date().toISOString(), params: {}, download_url: '/api/jobs/vid_one/download' };
const token = 'a'.repeat(43);
const result = { url: `/export.html#vid_one.${token}`, expires_at: Date.now() / 1000 + 600 };
const setup = window => {
  window.scrollTo = () => {};
  Object.defineProperty(window.navigator, 'userAgent', { value: 'iPhone MicroMessenger' });
  window.sessionStorage.setItem('calligraphy.wechatNoticeDismissed', '1');
};
const byId = (ui, id) => ui.document.getElementById(`video-export-${id}`);
const open = ui => ui.document.querySelector('.btn-download').click();

test('WeChat download asks before creating a single-video link and supports copy/revoke', async t => {
  let copied;
  const ui = await createFrontend({ jobs: [job], setup(window) {
    setup(window);
    Object.defineProperty(window.navigator, 'clipboard', { value: { writeText: async value => { copied = value; } } });
  }, fetch({ url, options }) {
    if (url.endsWith('/export-link')) return jsonResponse(options.method === 'DELETE' ? {} : result);
  } });
  t.after(ui.close);
  open(ui);
  assert.equal(byId(ui, 'notice').open, true);
  assert.match(byId(ui, 'notice').textContent, /任何持有連結的人/);
  assert.equal(ui.requests.filter(r => r.url.endsWith('/export-link')).length, 0);
  byId(ui, 'create').click();
  byId(ui, 'create').click();
  await flush();
  assert.equal(ui.requests.filter(r => r.url.endsWith('/export-link')).length, 1);
  assert.equal(byId(ui, 'url').value, 'http://calligraphy.test' + result.url);
  byId(ui, 'copy').click();
  await flush();
  assert.equal(copied, byId(ui, 'url').value);
  byId(ui, 'revoke').click();
  await flush();
  assert.equal(byId(ui, 'url').value, '');
  assert.match(byId(ui, 'status').textContent, /已停用/);
});

test('clipboard fallback selects full link; closing pending creation does not reopen UI', async t => {
  let finish;
  const ui = await createFrontend({ jobs: [job], setup, fetch({ url }) {
    if (url.endsWith('/export-link')) return new Promise(resolve => { finish = resolve; });
  } });
  t.after(ui.close);
  open(ui);
  byId(ui, 'create').click();
  byId(ui, 'notice').close();
  finish(jsonResponse(result));
  await flush();
  assert.equal(byId(ui, 'notice').open, false);
  assert.equal(byId(ui, 'url').value, '');
  open(ui);
  byId(ui, 'create').click();
  finish(jsonResponse(result));
  await flush();
  byId(ui, 'copy').click();
  await flush();
  assert.equal(byId(ui, 'url').selectionEnd, byId(ui, 'url').value.length);
  assert.match(byId(ui, 'status').textContent, /長按/);
});

test('revoke serializes with create even across close/reopen', async t => {
  let finishDelete;
  const ui = await createFrontend({ jobs: [job], setup, fetch({ url, options }) {
    if (url.endsWith('/export-link')) return options.method === 'DELETE'
      ? new Promise(resolve => { finishDelete = resolve; }) : jsonResponse(result);
  } });
  t.after(ui.close);
  open(ui);
  byId(ui, 'create').click();
  await flush();
  byId(ui, 'revoke').click();
  assert.equal(byId(ui, 'create').disabled, true);
  byId(ui, 'notice').close();
  open(ui);
  byId(ui, 'create').click();
  assert.equal(ui.requests.filter(r => r.options.method === 'POST' && r.url.endsWith('/export-link')).length, 1);
  finishDelete(jsonResponse({}, 204));
  await flush();
  assert.equal(byId(ui, 'create').disabled, false);
  byId(ui, 'create').click();
  await flush();
  assert.equal(byId(ui, 'url').value, 'http://calligraphy.test' + result.url);
});

test('creation failure remains retryable; normal browser direct download is unchanged', async t => {
  const ui = await createFrontend({ jobs: [job], setup, fetch({ url }) {
    if (url.endsWith('/export-link')) return jsonResponse({ detail: '影片已到期' }, 404);
  } });
  t.after(ui.close);
  open(ui);
  byId(ui, 'create').click();
  await flush();
  assert.equal(byId(ui, 'create').disabled, false);
  assert.equal(byId(ui, 'copy').hidden, true);
  assert.match(byId(ui, 'status').textContent, /已到期/);
  const ordinary = await createFrontend({ jobs: [job] });
  t.after(ordinary.close);
  const event = new ordinary.window.MouseEvent('click', { bubbles: true, cancelable: true });
  ordinary.document.querySelector('.btn-download').dispatchEvent(event);
  assert.equal(event.defaultPrevented, false);
  assert.equal(byId(ordinary, 'notice').open, false);
  assert.equal(ordinary.requests.some(r => r.url.endsWith('/export-link')), false);
});
