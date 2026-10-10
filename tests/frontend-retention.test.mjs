import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const now = Date.now() / 1000;
const makeJob = (job_id, retention, extra = {}) => ({ job_id, job_type: 'render', status: 'succeeded', style: 'kai', text: '山水', retention, ...extra });
const dateTime = timestamp => new Date(timestamp * 1000).toLocaleString('zh-TW', {
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZoneName: 'short',
});

test('history and detail show exact server retention, including the active sharing extension', async t => {
  const ordinary = now + 23 * 3600;
  const shared = now + 72 * 3600;
  const jobs = [
    makeJob('ordinary', { expires_at: ordinary, ordinary_expires_at: ordinary, share_expires_at: null, output_available: true }),
    makeJob('shared', { expires_at: shared, ordinary_expires_at: now - 3600, share_expires_at: shared, output_available: true }),
  ];
  const ui = await createFrontend({ jobs }); t.after(ui.close);
  const notices = ui.document.querySelectorAll('.job-retention');
  assert.match(notices[0].textContent, /作品保留至/);
  assert.ok(notices[0].textContent.includes(dateTime(ordinary)));
  assert.doesNotMatch(notices[0].textContent, /分享延長/);
  assert.ok(notices[1].textContent.includes(dateTime(shared)));
  assert.match(notices[1].textContent, /分享延長/);
  ui.document.querySelector('[data-job-id="shared"] .btn-play-mini').click();
  const detail = ui.document.querySelector('[data-detail-retention]');
  assert.equal(detail.textContent, notices[1].textContent);
  assert.match(ui.document.getElementById('detail-meta').textContent, /分享連結期限/);
});

test('expired, missing, active and failed works do not imply a fresh 24-hour lifetime', async t => {
  const expiry = now - 30;
  const jobs = [
    makeJob('expired', { expires_at: expiry, output_available: true }),
    makeJob('missing', { expires_at: now + 600, output_available: false }),
    makeJob('queued', { expires_at: null }, { status: 'queued' }),
    makeJob('failed', { expires_at: now + 600 }, { status: 'failed' }),
    makeJob('unknown', undefined),
  ];
  const ui = await createFrontend({ jobs }); t.after(ui.close);
  const notice = id => ui.document.querySelector(`[data-job-id="${id}"] .job-retention`).textContent;
  assert.match(notice('expired'), /已到保留期限/);
  assert.match(notice('missing'), /檔案已移除/);
  assert.match(notice('queued'), /完成後顯示/);
  assert.match(notice('failed'), /記錄保留至/);
  assert.match(notice('unknown'), /暫未提供/);
  assert.doesNotMatch(notice('unknown'), /Invalid Date|24 小時/);
});

test('retention notes honor configured durations and distinguish 72-hour sharing from 10-minute handoff', async t => {
  const ui = await createFrontend({ fetch({ url }) {
    if (url === '/api/jobs') return jsonResponse({ jobs: [], retention_seconds: 120 });
  } }); t.after(ui.close);
  for (const label of ui.document.querySelectorAll('[data-retention-duration]')) assert.equal(label.textContent, '2 分鐘');
  const guide = ui.document.querySelector('.retention-guide').textContent;
  assert.match(guide, /未分享/); assert.match(guide, /72 小時/); assert.match(guide, /10 分鐘/); assert.match(guide, /不延長/);
  const handoff = ui.document.getElementById('video-export-notice').textContent;
  assert.match(handoff, /給自己/); assert.match(handoff, /任何持有連結的人都能觀看及下載/);
  assert.doesNotMatch(handoff, /只有你|僅本人|私人連結/);
});

test('ten-minute handoff creation and both copy paths retain exact expiry and access warning', async t => {
  for (const clipboardWorks of [true, false]) {
    const expires = now + 450;
    const ui = await createFrontend({ jobs: [makeJob('one')], setup(window) {
      window.scrollTo = () => {};
      Object.defineProperty(window.navigator, 'userAgent', { value: 'iPhone MicroMessenger' });
      window.sessionStorage.setItem('calligraphy.wechatNoticeDismissed', '1');
      if (clipboardWorks) Object.defineProperty(window.navigator, 'clipboard', { value: { writeText: async () => {} } });
    }, fetch({ url }) {
      if (url.endsWith('/export-link')) return jsonResponse({ url: '/export.html#one.' + 'a'.repeat(43), expires_at: expires });
    } }); t.after(ui.close);
    const byId = id => ui.document.getElementById('video-export-' + id);
    ui.document.querySelector('.btn-download').click();
    byId('create').click(); await flush();
    for (const copied of [false, true]) {
      if (copied) { byId('copy').click(); await flush(); }
      assert.ok(byId('status').textContent.includes(dateTime(expires)));
      assert.match(byId('status').textContent, /不延長作品保留期限/);
      assert.match(byId('status').textContent, /任何持有連結的人/);
    }
  }
});

test('share creation and revocation refresh history and open detail expiry without resetting playback', async t => {
  const ordinary = now + 3600, shared = now + 72 * 3600;
  let active = false;
  const current = () => makeJob('one', { expires_at: active ? shared : ordinary, ordinary_expires_at: ordinary, share_expires_at: active ? shared : null, output_available: true });
  const link = { url: '/watch.html#one.' + 'a'.repeat(43), expires_at: shared };
  const ui = await createFrontend({ fetch({url,options,body}) {
    if (url === '/api/jobs') return jsonResponse({jobs:[current()]});
    if (url.endsWith('/share-link/status')) return jsonResponse(active ? {active:true,...(body.token ? link : {expires_at:shared})} : {active:false});
    if (url.endsWith('/share-link')) { active = options.method !== 'DELETE'; return jsonResponse(active ? link : {}); }
  }}); t.after(ui.close);
  const d=ui.document;
  d.querySelector('.btn-play-mini').click();
  const video=d.querySelector('#detail-viewer video');
  d.getElementById('detail-share').click(); await flush();
  d.getElementById('video-share-create').click(); await flush(); await flush();
  assert.match(d.querySelector('.job-retention').textContent,/分享延長/);
  assert.match(d.querySelector('[data-detail-retention]').textContent,/分享延長/);
  assert.equal(d.querySelector('[data-detail-share-expiry]').hidden,false);
  assert.equal(d.querySelector('#detail-viewer video'),video);
  d.getElementById('video-share-revoke').click(); await flush(); await flush();
  assert.doesNotMatch(d.querySelector('[data-detail-retention]').textContent,/分享延長/);
  assert.equal(d.querySelector('[data-detail-share-expiry]').hidden,true);
  assert.equal(d.querySelector('#detail-viewer video'),video);
});
