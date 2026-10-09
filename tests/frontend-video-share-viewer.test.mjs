import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

const html = await readFile(new URL('../frontend/watch.html', import.meta.url), 'utf8');
const script = await readFile(new URL('../frontend/watch.js', import.meta.url), 'utf8');
const token = 'a'.repeat(43);
const second = 'b'.repeat(43);
const fragment = `#vid_one.${token}`;
const valid = () => ({ video_url: '/api/shares/vid_one/video', expires_at: Date.now() / 1000 + 3600 });
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const flush = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };

async function viewer(t, { hash = fragment, fetch, setup } = {}) {
  const dom = new JSDOM(html, { runScripts: 'outside-only', url: `https://calligraphy.test/watch.html${hash}` });
  const { window } = dom;
  const requests = [];
  const media = { play: 0, pause: 0, load: 0 };
  window.HTMLMediaElement.prototype.play = () => { media.play++; return Promise.resolve(); };
  window.HTMLMediaElement.prototype.pause = () => { media.pause++; };
  window.HTMLMediaElement.prototype.load = () => { media.load++; };
  window.fetch = async (url, options) => {
    requests.push({ url, options });
    return fetch ? fetch(url, options) : response(valid());
  };
  setup?.(window);
  window.eval(script);
  t.after(() => window.close());
  await flush();
  return { window, requests, media, get: id => window.document.getElementById(`watch-${id}`), document: window.document };
}

test('fresh standalone viewer exchanges body-only token and uses native cookie media without autoplay', async t => {
  const ui = await viewer(t);
  assert.equal(ui.requests.length, 1);
  const { url, options } = ui.requests[0];
  assert.equal(url, '/api/shares/vid_one/access');
  assert.equal(options.method, 'POST');
  assert.equal(options.credentials, 'same-origin');
  assert.equal(options.cache, 'no-store');
  assert.equal(options.referrerPolicy, 'no-referrer');
  assert.equal(options.headers['Content-Type'], 'application/x-www-form-urlencoded');
  assert.equal(options.body, `token=${token}`);
  assert.equal(ui.get('video').src, 'https://calligraphy.test/api/shares/vid_one/video');
  assert.equal(ui.get('video').controls, true);
  assert.equal(ui.get('video').hasAttribute('playsinline'), true);
  assert.equal(ui.get('video').preload, 'metadata');
  assert.equal(ui.get('video').hidden, false);
  assert.equal(ui.get('video').autoplay, false);
  assert.equal(ui.media.play, 0);
  assert.equal(ui.get('download').href, 'https://calligraphy.test/api/shares/vid_one/video?download=1');
  assert.equal(ui.get('download').download, 'calligraphy_video.mp4');
  assert.match(ui.get('status').textContent, /連結有效至/);
  assert.equal(ui.window.location.hash, fragment);
  assert.equal(ui.window.document.cookie, '');
  assert.equal(ui.window.localStorage.length, 0);
  assert.equal(ui.window.sessionStorage.length, 0);
  assert.equal(ui.document.querySelector('meta[name=referrer]').content, 'no-referrer');
  for (const element of ui.document.querySelectorAll('[href], [src]')) {
    const value = element.getAttribute('href') || element.getAttribute('src');
    assert.equal(value.includes(token), false);
    assert.equal(value.startsWith('http'), false);
  }
});

test('malformed fragments never make a request or expose media', async t => {
  for (const hash of ['', '#bad', `#vid.one.${token}`, `#${'a'.repeat(65)}.${token}`, `#vid_one.${token}x`, `#vid_one.${token}?tracking=1`]) {
    const ui = await viewer(t, { hash });
    assert.equal(ui.requests.length, 0);
    assert.equal(ui.get('video').hidden, true);
    assert.equal(ui.get('video').hasAttribute('src'), false);
    assert.equal(ui.get('download').hasAttribute('href'), false);
    assert.equal(ui.get('copy').hidden, true);
    assert.match(ui.get('status').textContent, /不完整/);
  }
});

test('expired, revoked or deleted videos show generic recovery without echoing server details', async t => {
  const ui = await viewer(t, { fetch: () => response({ detail: `<script>${token}</script>` }, 404) });
  assert.match(ui.get('status').textContent, /已到期、已停用/);
  assert.equal(ui.document.body.textContent.includes(token), false);
  assert.equal(ui.get('video').hidden, true);
  assert.equal(ui.get('download').hidden, true);
  assert.equal(ui.get('retry').hidden, false);
});

test('network error and access rate limits stay retryable', async t => {
  let count = 0;
  const ui = await viewer(t, { fetch: () => {
    if (++count === 1) throw new Error('Network disconnected');
    return count === 2 ? response({}, 429) : response(valid());
  } });
  assert.match(ui.get('status').textContent, /連線不穩/);
  ui.get('retry').click();
  await flush();
  assert.match(ui.get('status').textContent, /稍候一分鐘/);
  ui.get('retry').click();
  await flush();
  assert.equal(ui.get('video').hidden, false);
  assert.equal(ui.get('retry').hidden, true);
});

test('unexpected source URL and non-finite or past expiry never become media', async t => {
  for (const body of [
    { ...valid(), video_url: `https://evil.test/${token}` },
    { ...valid(), video_url: `/api/shares/vid_two/video?token=${token}` },
    { ...valid(), expires_at: 'soon' },
    { ...valid(), expires_at: Date.now() / 1000 - 1 },
  ]) {
    const ui = await viewer(t, { fetch: () => response(body) });
    assert.equal(ui.get('video').hidden, true);
    assert.equal(ui.get('video').hasAttribute('src'), false);
    assert.equal(ui.get('download').hasAttribute('href'), false);
  }
});

test('hash navigation aborts old access and ignores a late response', async t => {
  let oldResponse;
  const ui = await viewer(t, { fetch: url => url.includes('vid_one') ? new Promise(resolve => { oldResponse = resolve; }) : response({ ...valid(), video_url: '/api/shares/vid_two/video' }) });
  const firstSignal = ui.requests[0].options.signal;
  ui.window.location.hash = `#vid_two.${second}`;
  await new Promise(resolve => setTimeout(resolve, 20));
  await flush();
  assert.equal(firstSignal.aborted, true);
  assert.match(ui.get('video').src, /vid_two\/video$/);
  oldResponse(response(valid()));
  await flush();
  assert.match(ui.get('video').src, /vid_two\/video$/);
  assert.equal(ui.requests[1].options.body, `token=${second}`);
});

test('invalid hash clears previously authorized native playback immediately', async t => {
  const ui = await viewer(t);
  ui.window.location.hash = '#broken';
  await new Promise(resolve => setTimeout(resolve, 20));
  await flush();
  assert.equal(ui.get('video').hidden, true);
  assert.equal(ui.get('video').hasAttribute('src'), false);
  assert.equal(ui.get('download').hasAttribute('href'), false);
  assert.equal(ui.media.pause >= 2, true);
  assert.equal(ui.requests.length, 1);
});

test('pagehide ignores a late access response and never restores a dismissed player', async t => {
  let finish;
  const ui = await viewer(t, { fetch: () => new Promise(resolve => { finish = resolve; }) });
  ui.window.dispatchEvent(new ui.window.PageTransitionEvent('pagehide'));
  assert.equal(ui.requests[0].options.signal.aborted, true);
  finish(response(valid()));
  await flush();
  assert.equal(ui.get('video').hidden, true);
  assert.equal(ui.get('video').hasAttribute('src'), false);
  assert.equal(ui.get('download').hasAttribute('href'), false);
  assert.equal(ui.media.play, 0);
});

test('BFCache restore revalidates access and pagehide unloads media without replay', async t => {
  const ui = await viewer(t);
  ui.window.dispatchEvent(new ui.window.PageTransitionEvent('pagehide', { persisted: true }));
  assert.equal(ui.get('video').hasAttribute('src'), false);
  ui.window.dispatchEvent(new ui.window.PageTransitionEvent('pageshow', { persisted: true }));
  await flush();
  assert.equal(ui.requests.length, 2);
  assert.equal(ui.get('video').hidden, false);
  assert.equal(ui.media.play, 0);
  ui.window.dispatchEvent(new ui.window.PageTransitionEvent('pageshow', { persisted: false }));
  await flush();
  assert.equal(ui.requests.length, 2);
});

test('copy preserves full fragment for WeChat handoff; manual fallback selects it', async t => {
  let copied;
  const ui = await viewer(t, { setup(window) {
    Object.defineProperty(window.navigator, 'userAgent', { value: 'iPhone MicroMessenger' });
    Object.defineProperty(window.navigator, 'clipboard', { configurable: true, value: { writeText: async value => { copied = value; } } });
  } });
  assert.equal(ui.get('wechat').hidden, false);
  ui.get('copy').click();
  await flush();
  assert.equal(copied, 'https://calligraphy.test/watch.html' + fragment);
  assert.match(ui.get('copy-status').textContent, /已複製/);
  assert.match(ui.get('copy-status').textContent, /持有連結的人皆可觀看及下載/);
  assert.match(ui.get('copy-status').textContent, /到期時間/);
  assert.match(ui.document.querySelector('footer').textContent, /72 小時/);
  Object.defineProperty(ui.window.navigator, 'clipboard', { value: undefined });
  ui.get('copy').click();
  await flush();
  assert.equal(ui.get('link').value, copied);
  assert.equal(ui.get('link').selectionStart, 0);
  assert.equal(ui.get('link').selectionEnd, copied.length);
  assert.equal(ui.get('link-label').hidden, false);
  assert.match(ui.get('copy-status').textContent, /長按/);
  assert.match(ui.get('copy-status').textContent, /持有連結的人皆可觀看及下載/);
  assert.match(ui.get('copy-status').textContent, /到期時間/);
});

test('media error revalidates with token-free HEAD and clears a revoked video', async t => {
  const ui = await viewer(t, { fetch: (url, options) => options.method === 'HEAD' ? response({}, 404) : response(valid()) });
  ui.get('video').dispatchEvent(new ui.window.Event('error'));
  await flush();
  assert.equal(ui.requests[1].url, '/api/shares/vid_one/video');
  assert.equal(ui.requests[1].options.method, 'HEAD');
  assert.equal(ui.requests[1].options.credentials, 'same-origin');
  assert.equal(ui.requests[1].options.body, undefined);
  assert.equal(ui.get('video').hidden, true);
  assert.equal(ui.get('download').hasAttribute('href'), false);
  assert.match(ui.get('status').textContent, /已停用/);
});

test('expiry unloads the video and stale expiry cannot stop a newer share', async t => {
  const timers = [];
  const ui = await viewer(t, { setup(window) {
    window.setTimeout = callback => { timers.push(callback); return timers.length; };
    window.clearTimeout = () => {};
  }, fetch: url => response({ ...valid(), video_url: url.replace('/access', '/video') }) });
  const firstTimer = timers[0];
  ui.window.history.replaceState(null, '', `#vid_two.${second}`);
  ui.window.dispatchEvent(new ui.window.HashChangeEvent('hashchange'));
  await flush();
  firstTimer();
  assert.equal(ui.get('video').hidden, false);
  timers.at(-1)();
  assert.equal(ui.get('video').hidden, true);
  assert.equal(ui.get('download').hidden, true);
  assert.match(ui.get('status').textContent, /已到期/);
});
