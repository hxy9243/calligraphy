// The fragment is never transmitted as a URL, nor stored in cookies/storage.
// Preserve it so WeChat's browser-menu handoff can open the exact same link.
function updateExportForm() {
  const form = document.getElementById('export-form');
  const tokenField = document.getElementById('export-token');
  const message = document.getElementById('export-message');
  form.hidden = true;
  form.removeAttribute('action');
  tokenField.value = '';
  const match = location.hash.match(/^#([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]{43})$/);
  if (match) {
    form.action = `/api/exports/${match[1]}/download`;
    tokenField.value = match[2];
    form.hidden = false;
    message.textContent = '連結最長有效 10 分鐘。到期或影片已刪除時，請回原來的微信頁面重新建立。';
  } else {
    message.textContent = '下載連結不完整。請回原來的微信頁面重新複製影片連結。';
  }
}
updateExportForm();
window.addEventListener('hashchange', updateExportForm);
window.addEventListener('pageshow', updateExportForm);
