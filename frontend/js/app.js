/**
 * Calligraphy Workbench — app.js
 *
 * Three views, routed by hash:
 *   #create  — compose (text → font → layout → output) + live stage / latest result
 *   #history — browse past jobs, open full results, reuse parameters
 *   #fonts   — catalogue browser (metadata, licence, provenance)
 * The backend API is unchanged: /api/styles, /api/font-catalog, /api/convert-script,
 * /api/previews, /api/renders, /api/jobs[/id[/video|download|image]].
 */
import { PRESET_EXAMPLES, fallbackConvert } from './data.js';

const MAX_CHARS = 256;
const STORE = 'wb:v1';

const CATEGORY_LABEL = {
  engine: '笔画引擎', kaishu: '楷书', lishu: '隶书', songti: '宋体·雕版', fangsong: '仿宋', other: '行草·魏碑·其他',
};
const SUPPORT_LABEL = { trad: '繁体', simp: '简体', both: '繁简兼备' };
const CATEGORY_ORDER = ['engine', 'kaishu', 'lishu', 'songti', 'fangsong', 'other'];

// API style ids that differ from catalogue ids
const API_TO_CATALOG = { mashanzheng: 'mashanzheng-kai', 'lishu hanwang': 'hanwang-lisu-medium', longcang: 'longcang-xingshu' };
// Web-preview font files for styles that are not in the catalogue JSON
const EXTRA_FONT_FILES = { 'yuji-boku': 'YujiBoku-Regular.ttf', 'qiji-kai': 'qiji-combo.ttf' };
const EXTRA_META = {
  'qiji-kai': { name: '令東齊伋體楷書', en: 'LingDong Qiji Kai', category: 'kaishu', support: 'trad' },
  'aa shoujin': { name: '瘦金体', en: 'Shoujin', category: 'other', support: 'both' },
  'chiron-goround': { name: '昭源黑体', en: 'Chiron GoRound', category: 'other', support: 'both' },
  'yuji-boku': { name: '佑字木筆', en: 'Yuji Boku', category: 'other', support: 'both' },
  'hanwang-kandayan': { name: '王漢宗勘大顏', en: 'HanWang KanDaYan', category: 'other', support: 'trad' },
};
const ENGINE_STACK = '"KaiTi","Kaiti SC","STKaiti","BiauKai","AR PL UKai TW","Noto Serif SC",serif';

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ------------------------------------------------------------------ state */
const state = {
  script: 'simp', dir: 'vertical', size: 68, spacing: 0.18, fit: true, speed: 1, fps: 24,
  styleId: 'kai', recent: [], favs: [], theme: 'theme-xuan',
  entries: [], byId: new Map(), catalog: [],
  jobs: [], tracked: new Map(), jobSig: '',
  latest: null, historyFilter: 'all', historySearch: '',
  picker: { cat: 'all', sup: 'all', q: '' },
  fontFilters: { category: 'all', support: 'all', medium: 'all', q: '' },
  detailJob: null,
};

function loadStore() {
  try {
    const s = JSON.parse(localStorage.getItem(STORE) || '{}');
    for (const k of ['script', 'dir', 'size', 'spacing', 'fit', 'speed', 'fps', 'styleId', 'recent', 'favs', 'theme']) {
      if (s[k] !== undefined) state[k] = s[k];
    }
    return s;
  } catch { return {}; }
}
function saveStore() {
  try {
    localStorage.setItem(STORE, JSON.stringify({
      text: els.text.value, script: state.script, dir: state.dir, size: state.size, spacing: state.spacing,
      fit: state.fit, speed: state.speed, fps: state.fps, styleId: state.styleId,
      recent: state.recent, favs: state.favs, theme: state.theme,
    }));
  } catch { /* storage unavailable */ }
}

const els = {};
function bindEls() {
  Object.assign(els, {
    text: $('#text-input'), count: $('#char-count'), counter: $('#char-counter'), warning: $('#char-warning'),
    presetList: $('#preset-list'),
    fontCurrent: $('#font-current'), fontGlyph: $('#font-current-glyph'), fontName: $('#font-current-name'),
    fontSub: $('#font-current-sub'), fontRecent: $('#font-recent'), fontNote: $('#font-note'),
    sizeSlider: $('#size-slider'), sizeVal: $('#size-val'), spacingSlider: $('#spacing-slider'), spacingVal: $('#spacing-val'),
    fit: $('#fit-toggle'),
    btnPreview: $('#btn-preview'), btnRender: $('#btn-render'),
    viewport: $('#stage-viewport'), paper: $('#stage-paper'), stageText: $('#stage-text'), caption: $('#stage-caption'),
    canvasMeta: $('#canvas-meta'),
    paneLive: $('#pane-live'), paneResult: $('#pane-result'), tabLive: $('#tab-live'), tabResult: $('#tab-result'), resultDot: $('#result-dot'),
    resultEmpty: $('#result-empty'), resultBody: $('#result-body'), resultViewer: $('#result-viewer'),
    resultZoom: $('#result-zoom'), resultDownload: $('#result-download'),
    progress: $('#job-progress'), progressFill: $('#job-progress-fill'), progressText: $('#job-progress-text'),
    jobIndicator: $('#job-indicator'), jobIndicatorText: $('#job-indicator-text'),
    themeSelect: $('#theme-select'),
    historyGrid: $('#history-grid'), historyEmpty: $('#history-empty'), historySearch: $('#history-search'),
    fontsGrid: $('#fonts-grid'), fontsSearch: $('#fonts-search'), fontsSummary: $('#fonts-summary'),
    picker: $('#font-picker'), pickerList: $('#picker-list'), pickerSearch: $('#picker-search'),
    detail: $('#job-detail'), detailViewer: $('#detail-viewer'), detailMeta: $('#detail-meta'), detailText: $('#detail-text'),
    detailZoom: $('#detail-zoom'), detailDownload: $('#detail-download'), detailReuse: $('#detail-reuse'), detailTitle: $('#detail-title'),
    toasts: $('#toasts'),
  });
}

/* ------------------------------------------------------------------ utils */
function toast(msg, type = 'info', ms = 2800) {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  els.toasts.appendChild(t);
  setTimeout(() => t.remove(), ms);
}
async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = '';
    try { const j = await res.json(); detail = j.detail || j.message || ''; } catch { /* non-JSON */ }
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg || '').join('; ');
    throw new Error(detail || `请求失败 (${res.status})`);
  }
  return res.json();
}
const postJson = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const baseName = (p) => (p || '').split('/').pop();

function whenVisible(el, cb) {
  if (!('IntersectionObserver' in window)) { cb(); return; }
  whenVisible.io ||= new IntersectionObserver((items) => {
    for (const it of items) if (it.isIntersecting) { whenVisible.io.unobserve(it.target); it.target._cb(); }
  }, { rootMargin: '200px' });
  el._cb = cb;
  whenVisible.io.observe(el);
}

/* ------------------------------------------------------------------ fonts */
function buildEntries(apiStyles, catalog) {
  state.catalog = catalog;
  const metaById = new Map(catalog.map((m) => [m.id, m]));
  const entries = [];
  const covered = new Set();

  const make = (id, base) => ({ id, ...base });
  for (const s of apiStyles) {
    const metaId = metaById.has(s.id) ? s.id : API_TO_CATALOG[s.id];
    const meta = metaId ? metaById.get(metaId) : null;
    if (meta) covered.add(meta.id);
    if (s.type === 'stroke_ir') {
      entries.push(make(s.id, {
        name: s.name.replace(/\s*\(.*\)/, ''), en: s.description, category: 'engine', support: 'both',
        engine: true, sub: '笔画拟合书写 · 动画效果最佳', meta: null, file: null,
      }));
      continue;
    }
    const extra = EXTRA_META[s.id];
    const parenName = s.name.match(/^(.*?)\s*\((.*)\)$/);
    entries.push(make(s.id, {
      name: meta?.name_zh || extra?.name || (parenName ? parenName[1] : s.id),
      en: meta?.name_en || extra?.en || (parenName ? parenName[2] : ''),
      category: meta?.style_category || extra?.category || 'other',
      support: meta?.char_support || extra?.support || 'both',
      meta, file: meta ? baseName(meta.file_path) : EXTRA_FONT_FILES[s.id] || null,
    }));
  }
  for (const m of catalog) {
    if (covered.has(m.id)) continue;
    entries.push(make(m.id, {
      name: m.name_zh, en: m.name_en, category: m.style_category, support: m.char_support, meta: m,
      file: m.is_downloaded ? baseName(m.file_path) : null,
    }));
  }
  entries.forEach((e) => {
    e.family = e.engine ? ENGINE_STACK : (e.file ? `"wb-${e.id.replace(/[^a-z0-9]/gi, '_')}", "Noto Serif SC", serif` : '"Noto Serif SC", serif');
    e.sub = e.sub || [CATEGORY_LABEL[e.category], e.meta?.artist?.split(/[（(]/)[0]].filter(Boolean).join(' · ');
  });
  entries.sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category));
  state.entries = entries;
  state.byId = new Map(entries.map((e) => [e.id, e]));
  for (const [apiId, catId] of Object.entries(API_TO_CATALOG)) {
    if (!state.byId.has(catId) && state.byId.has(apiId)) state.byId.set(catId, state.byId.get(apiId));
  }
  registerFontFaces();
}

function registerFontFaces() {
  const rules = state.entries.filter((e) => e.file).map((e) => {
    const fam = e.family.match(/"(wb-[^"]+)"/)[1];
    const fmt = e.file.endsWith('.otf') ? 'opentype' : e.file.endsWith('.ttc') ? 'collection' : 'truetype';
    return `@font-face{font-family:"${fam}";src:url("/fonts/${encodeURIComponent(e.file)}") format("${fmt}");font-display:swap}`;
  });
  const style = document.createElement('style');
  style.textContent = rules.join('\n');
  document.head.appendChild(style);
}

const currentEntry = () => state.byId.get(state.styleId) || state.entries[0];
const entryName = (id) => state.byId.get(id)?.name || id;

function sampleFor(entry, max = 5) {
  const isTrad = (entry?.support === 'trad') || (entry?.support === 'both' && state.script === 'trad');
  const targetScript = isTrad ? 'trad' : 'simp';

  // 1. If entry has meta.sample_text, use its authentic classical demo words converted to font's support
  if (entry?.meta?.sample_text) {
    const cleaned = entry.meta.sample_text.replace(/[，。；：\s\n]/g, '');
    if (cleaned) {
      const conv = fallbackConvert(cleaned, targetScript);
      return [...conv].slice(0, max).join('');
    }
  }

  // 2. Otherwise check current user text
  const raw = (els.text?.value || '').replace(/\s+/g, '');
  if (raw) {
    const converted = fallbackConvert(raw, targetScript);
    if (converted) {
      return [...converted].slice(0, max).join('');
    }
  }

  // 3. Fallback curated calligraphy phrases
  return targetScript === 'trad'
    ? ['永和九年', '墨寶鑑賞', '風和日麗', '至公無私'][0].slice(0, max)
    : ['永和九年', '墨宝鉴赏', '风和日丽', '至公无私'][0].slice(0, max);
}

function selectFont(id, { silent = false } = {}) {
  const entry = state.byId.get(id);
  if (!entry) return;
  state.styleId = entry.id;
  state.recent = [entry.id, ...state.recent.filter((r) => r !== entry.id)].slice(0, 6);
  renderFontCard();
  applyStage();
  saveStore();
  // Follow the font's native script, as the legacy workbench did
  if (entry.support !== 'both' && state.script !== entry.support && els.text.value.trim()) {
    convertScript(entry.support, { auto: true });
  } else if (entry.support !== 'both') {
    setScriptButtons(entry.support);
    state.script = entry.support;
  }
  if (!silent) toast(`已选用「${entry.name}」`, 'success', 1600);
}

function renderFontCard() {
  const e = currentEntry();
  if (!e) return;
  els.fontGlyph.style.fontFamily = e.family;
  els.fontGlyph.textContent = sampleFor(e, 1);
  els.fontName.textContent = e.name;
  els.fontSub.textContent = [e.sub, e.support !== 'both' ? `${SUPPORT_LABEL[e.support]}字库` : '繁简兼备'].filter(Boolean).join(' · ');
  const note = e.meta?.aesthetic_notes || (e.engine ? '使用笔画拟合引擎书写，支持逐笔动画。' : '');
  els.fontNote.textContent = note;
  els.fontNote.className = 'note';
  els.fontRecent.innerHTML = '';
  state.recent.filter((id) => state.byId.has(id) && id !== e.id).slice(0, 5).forEach((id) => {
    const r = state.byId.get(id);
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'chip'; b.textContent = r.name; b.style.fontFamily = r.family;
    b.title = '最近使用';
    b.addEventListener('click', () => selectFont(id));
    els.fontRecent.appendChild(b);
  });
}

/* ---------------------------------------------------------------- stage */
function applyStage() {
  const e = currentEntry();
  const text = els.text.value || '永';
  els.stageText.textContent = text;
  els.stageText.style.fontFamily = e ? e.family : '';
  els.stageText.style.letterSpacing = `${state.spacing}em`;
  els.paper.classList.toggle('vertical', state.dir === 'vertical');
  els.paper.classList.toggle('horizontal', state.dir === 'horizontal');
  els.viewport.classList.toggle('horizontal', state.dir === 'horizontal');
  fitStage();
  if (e?.file) {
    const fam = e.family.match(/"(wb-[^"]+)"/)[1];
    document.fonts.load(`40px "${fam}"`, text.slice(0, 40)).then(fitStage).catch(() => {});
  }
}

function overflowing() {
  const v = els.viewport;
  const r = els.stageText.getBoundingClientRect();
  const cs = getComputedStyle(els.paper);
  return state.dir === 'vertical'
    ? r.width + parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight) > v.clientWidth + 1
    : r.height + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) > v.clientHeight + 1;
}
function fitStage() {
  const t = els.stageText;
  let size = state.size;
  t.style.fontSize = `${size}px`;
  if (state.fit && overflowing()) {
    let lo = 14, hi = size;
    while (hi - lo > 1) {
      const mid = Math.floor((lo + hi) / 2);
      t.style.fontSize = `${mid}px`;
      if (overflowing()) hi = mid; else lo = mid;
    }
    size = lo;
    t.style.fontSize = `${size}px`;
  }
  const shrunk = size < state.size;
  els.sizeVal.textContent = shrunk ? `${state.size}px → 适应 ${size}px` : `${state.size}px`;
  const len = [...els.text.value.replace(/\s/g, '')].length;
  els.caption.innerHTML = `<span>${len} 字 · ${state.dir === 'vertical' ? '竖排右起' : '横排'}</span><span>${shrunk ? '已自动缩小以完整呈现' : (overflowing() ? '内容较长，可在画布内滚动' : '')}</span>`;
  els.canvasMeta.textContent = currentEntry()?.name || '';
  if (state.dir === 'vertical') els.viewport.scrollLeft = els.viewport.scrollWidth; // keep the first column visible (right edge)
}

/* ------------------------------------------------------------------ text */
function updateText() {
  const len = els.text.value.length;
  els.count.textContent = len;
  const over = len > MAX_CHARS;
  els.counter.classList.toggle('exceeded', over);
  els.text.classList.toggle('exceeded', over);
  els.warning.hidden = !over;
  if (over) els.warning.textContent = `超出 ${len - MAX_CHARS} 字，请删减后再生成`;
  applyStage();
  renderFontCard();
  saveStore();
  return !over;
}

function setScriptButtons(script) {
  $$('[data-script]').forEach((b) => b.classList.toggle('active', b.dataset.script === script));
}
async function convertScript(target, { auto = false } = {}) {
  const original = els.text.value;
  state.script = target;
  setScriptButtons(target);
  if (original.trim()) {
    try { els.text.value = (await postJson('/api/convert-script', { text: original, target })).text; }
    catch { els.text.value = fallbackConvert(original, target); }
    if (auto) toast(`该字库以${SUPPORT_LABEL[target]}为主，文字已转为${SUPPORT_LABEL[target]}`, 'info', 2200);
  }
  updateText();
  renderPresets();
}

function renderPresets() {
  els.presetList.innerHTML = '';
  PRESET_EXAMPLES.forEach((p) => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'chip preset-chip'; b.textContent = p.name;
    b.addEventListener('click', () => {
      const e = currentEntry();
      const script = e && e.support !== 'both' ? e.support : state.script;
      els.text.value = script === 'trad' ? p.trad : p.simp;
      updateText();
    });
    els.presetList.appendChild(b);
  });
}

/* ---------------------------------------------------------------- picker */
function pickerEntries() {
  const { cat, sup, q } = state.picker;
  const needle = q.trim().toLowerCase();
  return state.entries.filter((e) => {
    if (cat === 'fav' ? !state.favs.includes(e.id) : (cat !== 'all' && e.category !== cat)) return false;
    if (sup !== 'all' && e.support !== 'both' && e.support !== sup) return false;
    if (needle) {
      const hay = [e.name, e.en, e.meta?.artist, e.meta?.style_display, e.meta?.historical_reference, e.meta?.font_author, e.id].join(' ').toLowerCase();
      if (!hay.includes(needle)) return false;
    }
    return true;
  });
}
function renderPicker() {
  const list = pickerEntries();
  els.pickerList.innerHTML = '';
  if (!list.length) {
    els.pickerList.innerHTML = '<li class="picker-empty">没有符合条件的字体</li>';
    return;
  }
  list.forEach((e) => {
    const li = document.createElement('li');
    li.className = 'picker-item';
    li.dataset.fontId = e.id;
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', String(e.id === state.styleId));
    li.innerHTML = `
      <div class="picker-sample">${esc(sampleFor(e, 3))}</div>
      <div class="picker-info"><strong>${esc(e.name)}</strong><small>${esc(e.sub)}</small>
        <div class="badges"><span class="badge font-badge-support ${e.support === 'both' ? '' : 'accent'}">${SUPPORT_LABEL[e.support]}</span></div></div>
      <button type="button" class="star ${state.favs.includes(e.id) ? 'on' : ''}" aria-label="收藏" title="收藏">${state.favs.includes(e.id) ? '★' : '☆'}</button>`;
    const sample = $('.picker-sample', li);
    whenVisible(sample, () => { sample.style.fontFamily = e.family; });
    $('.star', li).addEventListener('click', (ev) => {
      ev.stopPropagation();
      state.favs = state.favs.includes(e.id) ? state.favs.filter((f) => f !== e.id) : [...state.favs, e.id];
      saveStore(); renderPicker();
    });
    li.addEventListener('click', () => { selectFont(e.id); els.picker.close(); });
    els.pickerList.appendChild(li);
  });
  $('.picker-item[aria-selected="true"]', els.pickerList)?.scrollIntoView({ block: 'center' });
}
function openPicker() {
  els.pickerSearch.value = state.picker.q = '';
  renderPicker();
  els.picker.showModal();
}

/* -------------------------------------------------------------- viewers */
function mountMedia(viewer, zoomBtn, dl, media) {
  viewer.classList.remove('actual');
  viewer.innerHTML = '';
  if (media.kind === 'video') {
    const v = document.createElement('video');
    v.src = media.src; v.controls = true; v.loop = true; v.muted = true; v.autoplay = true; v.playsInline = true;
    v.play?.().catch(() => {});
    viewer.appendChild(v);
    zoomBtn.hidden = true;
  } else {
    const img = document.createElement('img');
    img.src = media.src; img.alt = '书法成品';
    viewer.appendChild(img);
    zoomBtn.hidden = false;
    zoomBtn.textContent = '实际大小';
  }
  dl.href = media.download || media.src;
  dl.setAttribute('download', media.filename || '');
}
function bindZoom(btn, viewer) {
  btn.addEventListener('click', () => {
    const actual = viewer.classList.toggle('actual');
    btn.textContent = actual ? '适应窗口' : '实际大小';
  });
}

function mediaForJob(j) {
  if (j.status !== 'succeeded') return null;
  if (j.job_type === 'render') {
    return { kind: 'video', src: j.video_url || `/api/jobs/${j.job_id}/video`, download: j.download_url || `/api/jobs/${j.job_id}/download`, filename: `calligraphy_${j.job_id}.mp4` };
  }
  const ext = (j.output_path || '').toLowerCase().endsWith('.png') ? 'png' : 'svg';
  return { kind: 'image', src: j.download_url || `/api/jobs/${j.job_id}/image`, download: `/api/jobs/${j.job_id}/image`, filename: `calligraphy_${j.job_id}.${ext}` };
}

function setLatest(media) {
  state.latest = media;
  els.resultEmpty.hidden = true;
  els.resultBody.hidden = false;
  mountMedia(els.resultViewer, els.resultZoom, els.resultDownload, media);
}
function setCanvasTab(tab) {
  const live = tab === 'live';
  els.paneLive.hidden = !live;
  els.paneResult.hidden = live;
  els.tabLive.classList.toggle('active', live); els.tabLive.setAttribute('aria-selected', String(live));
  els.tabResult.classList.toggle('active', !live); els.tabResult.setAttribute('aria-selected', String(!live));
  if (!live) els.resultDot.hidden = true;
  else applyStage();
}
function showResult(media) {
  setLatest(media);
  if (location.hash.replace('#', '') === 'create' || !location.hash) setCanvasTab('result');
  else els.resultDot.hidden = false;
  els.resultDot.hidden = !els.paneResult.hidden;
  $('.canvas').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ------------------------------------------------------------- actions */
function validate() {
  if (!els.text.value.trim()) { toast('请输入要书写的文本', 'error'); return false; }
  if (!updateText()) { toast(`字数超出 ${MAX_CHARS} 字上限`, 'error'); return false; }
  return true;
}

async function doPreview() {
  if (!validate()) return;
  els.btnPreview.disabled = true;
  showProgress('正在生成静图…', null);
  try {
    const data = await postJson('/api/previews', { text: els.text.value.trim(), style: state.styleId, format: 'auto', spacing: state.spacing });
    const ext = data.svg ? 'svg' : 'png';
    showResult({ kind: 'image', src: data.preview_url, download: data.preview_url, filename: `calligraphy_${data.job_id}.${ext}` });
    toast('静图已生成', 'success');
    refreshJobs();
  } catch (e) {
    toast(`静图失败：${e.message}`, 'error', 4500);
  } finally {
    els.btnPreview.disabled = false;
    hideProgress();
  }
}

async function doRender() {
  if (!validate()) return;
  els.btnRender.disabled = true;
  try {
    const data = await postJson('/api/renders', { text: els.text.value.trim(), style: state.styleId, speed: state.speed, fps: state.fps, spacing: state.spacing });
    toast('视频任务已入队，可在「历史」查看进度', 'info');
    track(data.job_id);
    refreshJobs();
  } catch (e) {
    toast(`提交失败：${e.message}`, 'error', 4500);
  } finally {
    els.btnRender.disabled = false;
  }
}

function showProgress(text, pct) {
  els.progress.hidden = false;
  els.progressText.textContent = text;
  els.progressFill.style.width = pct == null ? '35%' : `${Math.round(pct * 100)}%`;
}
function hideProgress() { els.progress.hidden = true; }

/* ----------------------------------------------------------------- jobs */
function track(jobId) {
  if (state.tracked.has(jobId)) return;
  let attempts = 0;
  const timer = setInterval(async () => {
    attempts++;
    try {
      const job = await api(`/api/jobs/${jobId}`);
      if (job.status === 'succeeded') {
        stopTrack(jobId);
        await refreshJobs();
        toast('书写视频已生成', 'success');
        const m = mediaForJob(job);
        if (m) showResult(m);
      } else if (job.status === 'failed') {
        stopTrack(jobId);
        toast(`渲染失败：${job.error_message || '未知错误'}`, 'error', 5000);
        refreshJobs();
      } else {
        state.tracked.get(jobId).progress = job.progress || 0;
        refreshJobs();
      }
    } catch (e) { console.warn(e); }
    if (attempts > 600) stopTrack(jobId);
    updateActiveUi();
  }, 1500);
  state.tracked.set(jobId, { timer, progress: 0 });
  updateActiveUi();
}
function stopTrack(jobId) {
  const t = state.tracked.get(jobId);
  if (t) clearInterval(t.timer);
  state.tracked.delete(jobId);
  updateActiveUi();
}

const isActive = (j) => j.status === 'queued' || j.status === 'running';
function updateActiveUi() {
  const active = state.jobs.filter(isActive);
  $$('[data-history-count]').forEach((b) => { b.hidden = !active.length; b.textContent = active.length; });
  els.jobIndicator.hidden = !active.length;
  els.jobIndicatorText.textContent = `渲染中 ${active.length}`;
  if (active.length) {
    const avg = active.reduce((s, j) => s + (j.progress || 0), 0) / active.length;
    showProgress(`书写视频渲染中 · ${Math.round(avg * 100)}%（${active.length} 个任务）`, avg);
  } else if (!els.btnPreview.disabled) {
    hideProgress();
  }
}

async function refreshJobs() {
  try {
    const { jobs } = await api('/api/jobs');
    state.jobs = jobs || [];
    state.jobs.filter(isActive).forEach((j) => track(j.job_id));
    const sig = state.jobs.map((j) => `${j.job_id}:${j.status}:${Math.round((j.progress || 0) * 20)}`).join('|');
    if (sig !== state.jobSig) { state.jobSig = sig; renderHistory(); }
    updateActiveUi();
  } catch (e) { console.warn('jobs', e); }
}

function fmtTime(s) {
  if (!s) return '';
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s.replace(' ', 'T') + 'Z');
  if (Number.isNaN(d.getTime())) return s.slice(5, 16).replace('T', ' ');
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
const STATUS_LABEL = { succeeded: '完成', failed: '失败', queued: '排队中', running: '渲染中' };

function renderHistory() {
  const f = state.historyFilter;
  const q = state.historySearch.trim().toLowerCase();
  const list = state.jobs.filter((j) => {
    if (f === 'render' || f === 'preview') { if (j.job_type !== f) return false; }
    if (f === 'active' && !isActive(j)) return false;
    if (f === 'failed' && j.status !== 'failed') return false;
    if (q && !(`${j.text} ${entryName(j.style)} ${j.style}`.toLowerCase().includes(q))) return false;
    return true;
  });
  els.historyGrid.innerHTML = '';
  els.historyEmpty.hidden = list.length > 0;
  els.historyEmpty.querySelector('p').textContent = state.jobs.length ? '没有符合筛选的记录' : '暂无记录';
  list.forEach((j) => {
    const card = document.createElement('button');
    card.type = 'button'; card.className = 'job-card';
    const media = mediaForJob(j);
    const pct = Math.round((j.progress || 0) * 100);
    card.innerHTML = `
      <div class="job-thumb"><span class="job-kind">${j.job_type === 'render' ? '视频' : '静图'}</span></div>
      <div class="job-body">
        <div class="job-text">${esc(j.text)}</div>
        <div class="job-meta"><span>${esc(entryName(j.style))} · ${esc(fmtTime(j.created_at))}</span>
          <span class="status ${esc(j.status)}">${STATUS_LABEL[j.status] || esc(j.status)}</span></div>
        ${isActive(j) ? `<div class="mini-bar"><i style="width:${pct}%"></i></div>` : ''}
      </div>`;
    const thumb = $('.job-thumb', card);
    if (media) {
      whenVisible(thumb, () => {
        const el = document.createElement(media.kind === 'video' ? 'video' : 'img');
        if (media.kind === 'video') { el.muted = true; el.preload = 'metadata'; el.playsInline = true; el.src = `${media.src}#t=0.2`; }
        else { el.src = media.src; el.alt = ''; el.loading = 'lazy'; }
        thumb.prepend(el);
      });
    } else {
      const ph = document.createElement('div');
      ph.className = 'placeholder';
      ph.textContent = j.status === 'failed' ? '生成失败' : '处理中…';
      thumb.prepend(ph);
    }
    card.addEventListener('click', () => openDetail(j));
    els.historyGrid.appendChild(card);
  });
}

function openDetail(j) {
  state.detailJob = j;
  const media = mediaForJob(j);
  els.detailTitle.textContent = j.job_type === 'render' ? '书写视频' : '静图成品';
  els.detailViewer.classList.remove('actual');
  if (media) {
    mountMedia(els.detailViewer, els.detailZoom, els.detailDownload, media);
    els.detailDownload.hidden = false;
  } else {
    els.detailViewer.innerHTML = `<div class="empty"><p>${j.status === 'failed' ? '生成失败' : '尚未完成'}</p><small>${esc(j.error_message || '')}</small></div>`;
    els.detailZoom.hidden = true; els.detailDownload.hidden = true;
  }
  const p = j.params || {};
  const rows = [
    ['字体', entryName(j.style)],
    ['状态', STATUS_LABEL[j.status] || j.status],
    ['时间', fmtTime(j.created_at)],
    ['字数', `${[...j.text.replace(/\s/g, '')].length} 字`],
    p.spacing != null ? ['字距', `${p.spacing}em`] : null,
    p.speed != null ? ['速度', `${p.speed}x`] : null,
    p.fps != null ? ['帧率', `${p.fps} fps`] : null,
  ].filter(Boolean);
  els.detailMeta.innerHTML = rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('');
  els.detailText.textContent = j.text;
  els.detail.showModal();
}
function reuseJob(j) {
  els.text.value = j.text;
  if (state.byId.has(j.style)) { state.styleId = state.byId.get(j.style).id; }
  const p = j.params || {};
  if (p.spacing != null) { state.spacing = p.spacing; els.spacingSlider.value = p.spacing; els.spacingVal.textContent = `${p.spacing}em`; }
  if (p.speed != null) setSeg('#speed-seg', 'speed', p.speed, (v) => { state.speed = v; });
  if (p.fps != null) setSeg('#fps-seg', 'fps', p.fps, (v) => { state.fps = v; });
  els.detail.close();
  location.hash = '#create';
  setCanvasTab('live');
  renderFontCard(); updateText();
}

/* ----------------------------------------------------------- fonts view */
function renderFontsView() {
  const f = state.fontFilters;
  const needle = f.q.trim().toLowerCase();
  const list = state.catalog.filter((m) => {
    if (f.category !== 'all' && m.style_category !== f.category) return false;
    if (f.support === 'trad' && !['trad', 'both'].includes(m.char_support)) return false;
    if (f.support === 'simp' && !['simp', 'both'].includes(m.char_support)) return false;
    if (f.support === 'both' && m.char_support !== 'both') return false;
    if (f.medium !== 'all' && m.medium !== f.medium) return false;
    if (needle) {
      const hay = [m.name_zh, m.name_en, m.artist, m.style_display, m.historical_reference, m.font_author].join(' ').toLowerCase();
      if (!hay.includes(needle)) return false;
    }
    return true;
  });
  const counts = {};
  state.catalog.forEach((m) => { counts[m.style_category] = (counts[m.style_category] || 0) + 1; });
  els.fontsSummary.textContent = `共 ${state.catalog.length} 款离线字库 · ${Object.entries(counts).map(([k, v]) => `${CATEGORY_LABEL[k] || k} ${v}`).join(' · ')} · 当前显示 ${list.length}`;
  els.fontsGrid.innerHTML = '';
  if (!list.length) {
    els.fontsGrid.innerHTML = '<div class="empty" style="grid-column:1/-1"><p>没有符合条件的字库</p><small>试试放宽筛选条件。</small></div>';
    return;
  }
  list.forEach((m) => {
    const entry = state.entries.find((e) => e.meta?.id === m.id) || state.byId.get(m.id);
    const card = document.createElement('article');
    card.className = 'font-card';
    card.dataset.fontId = m.id;
    card.innerHTML = `
      <div><h3>${esc(m.name_zh)}</h3><div class="en">${esc(m.name_en)}</div></div>
      <div class="badges">
        <span class="badge accent">${esc(m.style_display)}</span>
        <span class="badge font-badge-support">${SUPPORT_LABEL[m.char_support] || ''}</span>
        <span class="badge">${m.medium === 'brush' ? '毛笔' : '硬笔'}</span>
      </div>
      <div class="glyph-sample">${esc(sampleFor(entry || { support: m.char_support, meta: m }, 6))}</div>
      <div class="aesthetic">${esc(m.aesthetic_notes)}</div>
      <details><summary>出处与协议</summary>
        <dl class="meta-list">
          <dt>名家</dt><dd>${esc(m.artist)} · ${esc(m.dynasty_era)}</dd>
          <dt>法帖</dt><dd>${esc(m.historical_reference || '历代名家书道真迹')}</dd>
          <dt>造字</dt><dd>${esc(m.font_author)}</dd>
          <dt>协议</dt><dd>${esc(m.license)}</dd>
        </dl>
      </details>
      <div class="btn-row">
        <button type="button" class="btn btn-primary btn-sm" data-use>✍ 用此字体创作</button>
        <a class="btn btn-secondary btn-sm" href="${esc(m.source_url)}" target="_blank" rel="noopener noreferrer">源项目</a>
      </div>`;
    const sample = $('.glyph-sample', card);
    if (entry) whenVisible(sample, () => { sample.style.fontFamily = entry.family; });
    $('[data-use]', card).addEventListener('click', () => {
      if (entry) selectFont(entry.id);
      location.hash = '#create';
      setCanvasTab('live');
    });
    els.fontsGrid.appendChild(card);
  });
}

/* ---------------------------------------------------------------- misc UI */
function setSeg(sel, attr, value, apply) {
  $$(`${sel} .seg-btn`).forEach((b) => b.classList.toggle('active', parseFloat(b.dataset[attr]) === parseFloat(value)));
  apply(parseFloat(value));
}
function applyTheme(theme) {
  document.body.classList.remove('theme-xuan', 'theme-gold', 'theme-rubbing');
  document.body.classList.add(theme);
  state.theme = theme;
  els.themeSelect.value = theme;
  document.querySelector('meta[name="theme-color"]').content = theme === 'theme-rubbing' ? '#1a1a1a' : '#f7f4ed';
}

function route() {
  const view = ['create', 'history', 'fonts'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'create';
  document.body.dataset.view = view;
  $$('.view').forEach((v) => { v.hidden = v.id !== `view-${view}`; });
  $$('[data-nav]').forEach((a) => (a.dataset.nav === view ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current')));
  window.scrollTo(0, 0);
  if (view === 'history') refreshJobs();
  if (view === 'create') applyStage();
  if (view === 'fonts') renderFontsView();
}

function bindChips(container, attr, onChange) {
  container.addEventListener('click', (ev) => {
    const b = ev.target.closest('.chip');
    if (!b) return;
    $$('.chip', container).forEach((c) => c.classList.toggle('active', c === b));
    onChange(b.dataset[attr]);
  });
}

function bindUi() {
  els.text.addEventListener('input', updateText);
  $$('[data-script]').forEach((b) => b.addEventListener('click', () => { if (b.dataset.script !== state.script || true) convertScript(b.dataset.script); }));
  els.fontCurrent.addEventListener('click', openPicker);

  $$('[data-dir]').forEach((b) => b.addEventListener('click', () => {
    state.dir = b.dataset.dir;
    $$('[data-dir]').forEach((x) => x.classList.toggle('active', x === b));
    applyStage(); saveStore();
  }));
  els.sizeSlider.addEventListener('input', () => { state.size = +els.sizeSlider.value; applyStage(); saveStore(); });
  els.spacingSlider.addEventListener('input', () => { state.spacing = +els.spacingSlider.value; els.spacingVal.textContent = `${state.spacing}em`; applyStage(); saveStore(); });
  els.fit.addEventListener('change', () => { state.fit = els.fit.checked; applyStage(); saveStore(); });
  $$('#speed-seg .seg-btn').forEach((b) => b.addEventListener('click', () => { setSeg('#speed-seg', 'speed', b.dataset.speed, (v) => { state.speed = v; }); saveStore(); }));
  $$('#fps-seg .seg-btn').forEach((b) => b.addEventListener('click', () => { setSeg('#fps-seg', 'fps', b.dataset.fps, (v) => { state.fps = v; }); saveStore(); }));

  els.btnPreview.addEventListener('click', doPreview);
  els.btnRender.addEventListener('click', doRender);
  els.tabLive.addEventListener('click', () => setCanvasTab('live'));
  els.tabResult.addEventListener('click', () => setCanvasTab('result'));
  bindZoom(els.resultZoom, els.resultViewer);
  bindZoom(els.detailZoom, els.detailViewer);
  els.detailReuse.addEventListener('click', () => state.detailJob && reuseJob(state.detailJob));
  els.themeSelect.addEventListener('change', () => { applyTheme(els.themeSelect.value); saveStore(); });

  // dialogs: close buttons, backdrop click, stop media on close
  $$('dialog').forEach((d) => {
    $$('[data-close]', d).forEach((b) => b.addEventListener('click', () => d.close()));
    d.addEventListener('click', (ev) => { if (ev.target === d) d.close(); });
  });
  els.detail.addEventListener('close', () => { els.detailViewer.innerHTML = ''; });

  // picker
  els.pickerSearch.addEventListener('input', () => { state.picker.q = els.pickerSearch.value; renderPicker(); });
  bindChips($('#picker-cats'), 'cat', (v) => { state.picker.cat = v; renderPicker(); });
  bindChips($('#picker-support'), 'sup', (v) => { state.picker.sup = v; renderPicker(); });

  // history
  bindChips($('#history-filters'), 'hf', (v) => { state.historyFilter = v; renderHistory(); });
  els.historySearch.addEventListener('input', () => { state.historySearch = els.historySearch.value; renderHistory(); });

  // fonts view
  els.fontsSearch.addEventListener('input', () => { state.fontFilters.q = els.fontsSearch.value; renderFontsView(); });
  $$('#view-fonts [data-filter]').forEach((group) => bindChips(group, 'val', (v) => { state.fontFilters[group.dataset.filter] = v; renderFontsView(); }));

  let resizeTimer;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(fitStage, 120); });
  window.addEventListener('hashchange', route);
}

/* ------------------------------------------------------------------ init */
async function init() {
  bindEls();
  const saved = loadStore();
  if (saved.text) els.text.value = saved.text;
  applyTheme(state.theme);
  els.sizeSlider.value = state.size;
  els.spacingSlider.value = state.spacing; els.spacingVal.textContent = `${state.spacing}em`;
  els.fit.checked = state.fit;
  $$('[data-dir]').forEach((x) => x.classList.toggle('active', x.dataset.dir === state.dir));
  setScriptButtons(state.script);
  setSeg('#speed-seg', 'speed', state.speed, (v) => { state.speed = v; });
  setSeg('#fps-seg', 'fps', state.fps, (v) => { state.fps = v; });
  bindUi();
  renderPresets();

  const [styles, catalog] = await Promise.all([
    api('/api/styles').then((d) => d.styles || []).catch(() => []),
    api('/api/font-catalog').catch(() => []),
  ]);
  buildEntries(styles.length ? styles : [{ id: 'kai', name: '楷书 (Kai)', description: '', type: 'stroke_ir' }], catalog);
  if (!state.byId.has(state.styleId)) state.styleId = state.byId.has('kai') ? 'kai' : state.entries[0].id;

  els.count.textContent = els.text.value.length;
  renderFontCard();
  if (els.picker?.open) renderPicker();
  updateText();
  route();
  await refreshJobs();
  const lastDone = state.jobs.find((j) => j.status === 'succeeded');
  if (lastDone) { const m = mediaForJob(lastDone); if (m) setLatest(m); }
}

document.addEventListener('DOMContentLoaded', init);
