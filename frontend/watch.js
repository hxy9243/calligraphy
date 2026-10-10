// A fragment bearer is exchanged in a bounded POST body. Media URLs contain no
// token; native playback/download use an HttpOnly, per-video capability cookie.
// Preserve the fragment for WeChat's browser-menu handoff and explicit copying.
const isExport = document.body.dataset.videoKind === 'export';
const apiKind = isExport ? 'exports' : 'shares';
const ttlMilliseconds = (isExport ? 600 : 72 * 3600) * 1000;
const video = document.getElementById('watch-video');
const status = document.getElementById('watch-status');
const download = document.getElementById('watch-download');
const retry = document.getElementById('watch-retry');
const copy = document.getElementById('watch-copy');
const copyStatus = document.getElementById('watch-copy-status');
const link = document.getElementById('watch-link');
const linkLabel = document.getElementById('watch-link-label');
const unavailable = isExport
  ? '影片連結已到期、已停用，或影片已移除。請回原來的微信頁面重新建立。'
  : '影片連結已到期、已停用，或影片已移除。請向分享者索取新連結。';
let generation = 0;
let controller;
let expiresTimer;
let mediaUrl = '';
let shareExpiresAt = null;

function copyNotice() {
  const expiry = shareExpiresAt ? `到期時間：${new Date(shareExpiresAt * 1000).toLocaleString('zh-Hant')}。` : isExport ? '臨時連結最長有效 10 分鐘。' : '連結自建立起有效 72 小時。';
  return `持有連結的人皆可觀看及下載這部影片。${expiry}${isExport ? "臨時瀏覽器連結，請勿轉傳。" : ""}分享者停用或移除影片後會提早失效。`;
}

document.getElementById('watch-wechat').hidden = !/MicroMessenger/i.test(navigator.userAgent);

function stopVideo() {
  video.pause();
  video.removeAttribute('src');
  video.load();
  video.hidden = true;
  download.hidden = true;
  download.removeAttribute('href');
  mediaUrl = '';
}

function showUnavailable() {
  stopVideo();
  status.textContent = unavailable;
  retry.hidden = false;
  retry.disabled = false;
}

async function loadShare() {
  const current = ++generation;
  controller?.abort();
  controller = new AbortController();
  clearTimeout(expiresTimer);
  stopVideo();
  retry.hidden = true;
  copy.hidden = true;
  copy.disabled = false;
  copyStatus.textContent = '';
  link.hidden = true;
  linkLabel.hidden = true;
  link.value = '';
  shareExpiresAt = null;
  const match = location.hash.match(/^#([A-Za-z0-9_-]{1,64})\.([A-Za-z0-9_-]{43})$/);
  if (!match) {
    status.textContent = isExport ? '影片連結不完整。請回原來的微信頁面重新複製完整連結。' : '影片連結不完整。請向分享者重新複製完整連結。';
    return;
  }
  copy.hidden = false;
  status.textContent = '正在讀取影片…';
  const expectedUrl = `/api/${apiKind}/${match[1]}/video`;
  try {
    const response = await fetch(`/api/${apiKind}/${match[1]}/access`, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      referrerPolicy: 'no-referrer', signal: controller.signal,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ token: match[2] }).toString(),
    });
    if (current !== generation) return;
    if (!response.ok) {
      if (response.status === 404 || response.status === 410) showUnavailable();
      else {
        status.textContent = response.status === 429 ? '開啟次數較多，請稍候一分鐘再試。' : '暫時無法讀取影片，請稍後重試。';
        retry.hidden = false;
      }
      return;
    }
    const data = await response.json();
    if (current !== generation) return;
    if (data.video_url !== expectedUrl || !Number.isFinite(data.expires_at) || data.expires_at * 1000 <= Date.now()) {
      showUnavailable();
      return;
    }
    mediaUrl = expectedUrl;
    shareExpiresAt = data.expires_at;
    video.src = mediaUrl;
    video.hidden = false;
    download.href = `${mediaUrl}?download=1`;
    download.hidden = false;
    status.textContent = `點選播放即可觀看。連結有效至 ${new Date(data.expires_at * 1000).toLocaleString('zh-Hant')}。`;
    expiresTimer = setTimeout(() => { if (current === generation) showUnavailable(); }, Math.min(data.expires_at * 1000 - Date.now(), ttlMilliseconds));
  } catch (error) {
    if (current !== generation || error.name === 'AbortError') return;
    status.textContent = '連線不穩或暫時無法讀取影片，請重新載入。';
    retry.hidden = false;
  }
}

retry.addEventListener('click', loadShare);
copy.addEventListener('click', async () => {
  if (copy.disabled) return;
  const current = generation;
  const url = location.href;
  copy.disabled = true;
  copyStatus.textContent = copyNotice();
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(url);
    if (current === generation) copyStatus.textContent = `已複製影片連結。${copyNotice()}`;
  } catch {
    if (current !== generation) return;
    link.value = url;
    link.hidden = false;
    linkLabel.hidden = false;
    link.focus();
    link.select();
    copyStatus.textContent = `請長按連結複製，再貼到 Safari／Chrome 開啟。${copyNotice()}`;
  } finally {
    if (current === generation) copy.disabled = false;
  }
});

video.addEventListener('error', async () => {
  if (!mediaUrl) return;
  const current = generation;
  const url = mediaUrl;
  try {
    const response = await fetch(url, { method: 'HEAD', credentials: 'same-origin', cache: 'no-store', referrerPolicy: 'no-referrer' });
    if (current !== generation || url !== mediaUrl) return;
    if (response.status === 404 || response.status === 410) { showUnavailable(); return; }
  } catch { /* Keep the retry guidance below for transient network failures. */ }
  if (current !== generation || url !== mediaUrl) return;
  status.textContent = '暫時無法播放，請重新載入；微信內可複製連結到 Safari／Chrome 再試。';
  retry.hidden = false;
});

window.addEventListener('hashchange', loadShare);
window.addEventListener('pageshow', event => { if (event.persisted) loadShare(); });
window.addEventListener('pagehide', () => {
  ++generation;
  controller?.abort();
  clearTimeout(expiresTimer);
  stopVideo();
});
loadShare();
