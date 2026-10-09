import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

test('accepted creation shows a separate popup and redirects after three seconds', async t => {
  let accept;
  const ui = await createFrontend({ fetch({ url }) {
    if (url === '/api/renders') return new Promise(resolve => { accept = resolve; });
  } });
  t.after(ui.close);
  const popup = ui.document.getElementById('creation-notice');
  ui.document.getElementById('btn-render').click();
  assert.equal(popup.open, false);
  accept(jsonResponse({ job_id: 'accepted' }, 202));
  await flush();
  assert.equal(popup.open, true);
  assert.equal(ui.document.getElementById('calligraphy-stage').contains(popup), false);
  assert.equal(ui.document.body.dataset.view, 'create');
  await ui.tickTimeouts(2999);
  assert.equal(popup.open, true);
  await ui.tickTimeouts(3000);
  assert.equal(popup.open, false);
  assert.equal(ui.window.location.hash, '#history');
  assert.equal(ui.document.body.dataset.view, 'history');
});

test('failed submissions never acknowledge or redirect; dismissal cancels automatic navigation', async t => {
  let fail = true;
  const ui = await createFrontend({ fetch({ url }) {
    if (url === '/api/renders') return jsonResponse(fail ? { detail: '請稍後再試' } : { job_id: 'accepted' }, fail ? 429 : 202);
  } });
  t.after(ui.close);
  const { document } = ui;
  const popup = document.getElementById('creation-notice');
  document.getElementById('btn-render').click();
  await flush();
  await ui.tickTimeouts(3000);
  assert.equal(popup.open, false);
  assert.equal(document.body.dataset.view, 'create');
  fail = false;
  document.getElementById('btn-render').click();
  await flush();
  assert.equal(popup.open, true);
  popup.querySelector('[data-close]').click();
  await ui.tickTimeouts(3000);
  assert.equal(document.body.dataset.view, 'create');
  document.getElementById('btn-render').click();
  await flush();
  document.getElementById('creation-view-history').click();
  assert.equal(popup.open, false);
  assert.equal(document.body.dataset.view, 'history');
});

const wechatSetup = window => {
  Object.defineProperty(window.navigator, 'userAgent', { value: 'Mozilla/5.0 iPhone MicroMessenger/8.0 Safari/604.1' });
  window.scrollTo = () => {};
};

test('WeChat notice offers copying and remembers dismissal for the tab', async t => {
  let copied;
  const ui = await createFrontend({ setup(window) {
    wechatSetup(window);
    Object.defineProperty(window.navigator, 'clipboard', { value: { writeText: async value => { copied = value; } } });
  } });
  t.after(ui.close);
  const popup = ui.document.getElementById('wechat-notice');
  assert.equal(popup.open, true);
  assert.match(popup.textContent, /不同瀏覽器的創作紀錄不會同步/);
  assert.equal(ui.document.getElementById('btn-render').disabled, false);
  ui.document.getElementById('wechat-copy-link').click();
  await flush();
  assert.equal(copied, ui.window.location.href);
  popup.querySelector('[data-close]').click();
  assert.equal(popup.open, false);
  assert.equal(ui.window.sessionStorage.getItem('calligraphy.wechatNoticeDismissed'), '1');
  const dismissed = await createFrontend({ setup(window) {
    wechatSetup(window);
    window.sessionStorage.setItem('calligraphy.wechatNoticeDismissed', '1');
  } });
  t.after(dismissed.close);
  assert.equal(dismissed.document.getElementById('wechat-notice').open, false);
});

test('clipboard failure selects the URL; ordinary browsers have no WeChat popup', async t => {
  const ui = await createFrontend({ setup: wechatSetup });
  t.after(ui.close);
  ui.document.getElementById('wechat-copy-link').click();
  await flush();
  const field = ui.document.getElementById('wechat-page-url');
  assert.equal(field.selectionStart, 0);
  assert.equal(field.selectionEnd, field.value.length);
  assert.match(ui.document.getElementById('wechat-copy-status').textContent, /長按/);
  const ordinary = await createFrontend();
  t.after(ordinary.close);
  assert.equal(ordinary.document.getElementById('wechat-notice').open, false);
  assert.equal(ordinary.document.querySelector('.topbar-tools').lastElementChild.className, 'github-star');
});
