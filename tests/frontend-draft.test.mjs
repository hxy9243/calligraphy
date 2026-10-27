import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';
const key = 'calligraphy.editorDraft';
const el = (ui, id) => ui.document.getElementById(id);
const saved = ui => JSON.parse(ui.window.localStorage.getItem(key));
const seed = value => window => window.localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
function edit(ui, id, value, event = 'input') {
  const control = el(ui, id);
  if (typeof value === 'boolean') control.checked = value; else control.value = value;
  control.dispatchEvent(new ui.window.Event(event, { bubbles: true }));
}
async function reload(ui, t) {
  const copy = await createFrontend({ setup: seed(saved(ui)) });
  t.after(copy.close); return copy;
}

test('personal Unicode draft, empty inscription and all composition controls survive reload', async t => {
  const ui = await createFrontend(); t.after(ui.close);
  edit(ui, 'text-input', '風雨𠮷\n明月 🌙');
  edit(ui, 'inscription-input', '');
  edit(ui, 'theme-select', 'theme-rubbing', 'change');
  edit(ui, 'paper-style-select', 'gold', 'change');
  edit(ui, 'paper-tone-select', 'cool', 'change');
  edit(ui, 'paper-decoration-select', 'bamboo', 'change');
  edit(ui, 'size-slider', '90'); edit(ui, 'spacing-slider', '0.4');
  edit(ui, 'fit-toggle', false, 'change'); edit(ui, 'zigzag-toggle', true, 'change');
  edit(ui, 'stamp-toggle', false, 'change');
  edit(ui, 'stamp-position-select', 'corner', 'change');
  edit(ui, 'stamp-url-input', 'https://example.com/my-seal');
  edit(ui, 'punctuation-select', 'break', 'change');
  el(ui, 'btn-horizontal').click();
  ui.document.querySelector('[data-cf="1:1"]').click();
  ui.document.querySelector('[data-speed="1.5"]').click();
  ui.document.querySelector('[data-fps="30"]').click();
  const before = saved(ui);
  const copy = await reload(ui, t);
  assert.deepEqual(saved(copy), before);
  for (const [id, value] of Object.entries(before.controls)) {
    assert.equal(typeof value === 'boolean' ? el(copy, id).checked : el(copy, id).value, value, id);
  }
  assert.equal(el(copy, 'btn-horizontal').getAttribute('aria-pressed'), 'true');
  assert.equal(el(copy, 'theme-select').value, 'theme-rubbing');
  assert.equal(el(copy, 'canvas-dim-val').textContent, '960 × 960');
});

test('last keystroke and intentional clearing are synchronous and survive a new session', async t => {
  const ui = await createFrontend(); t.after(ui.close);
  edit(ui, 'text-input', '末筆'); assert.equal(saved(ui).controls['text-input'], '末筆');
  edit(ui, 'text-input', ''); edit(ui, 'inscription-input', '');
  const copy = await reload(ui, t);
  assert.equal(el(copy, 'text-input').value, ''); assert.equal(el(copy, 'inscription-input').value, '');
  edit(copy, 'text-input', '新草稿');
  copy.window.dispatchEvent(new copy.window.Event('pagehide'));
  assert.equal(saved(copy).controls['text-input'], '新草稿');
});

test('opening history, replay, navigation and pagehide do not overwrite personal draft; editing adopts replay', async t => {
  const ui = await createFrontend({ jobs: [{job_id:'old', job_type:'render', status:'succeeded', text:'歷史作品', style:'kai', params:{palette:'light'}}] }); t.after(ui.close);
  edit(ui, 'text-input', '自己的草稿'); edit(ui, 'theme-select', 'theme-rubbing', 'change');
  const before = saved(ui);
  ui.document.querySelector('[data-job-id="old"] .job-text').click();
  el(ui, 'detail-reuse').click(); await flush();
  assert.equal(el(ui, 'text-input').value, '歷史作品');
  el(ui, 'text-input').click(); // Focus alone is not an edit.
  ui.document.querySelector('[data-nav="history"]').click();
  ui.document.querySelector('[data-nav="create"]').click();
  ui.window.dispatchEvent(new ui.window.Event('pagehide'));
  assert.deepEqual(saved(ui), before);
  const copy = await reload(ui, t); assert.equal(el(copy, 'text-input').value, '自己的草稿');
  edit(ui, 'text-input', '歷史作品修改');
  assert.equal(saved(ui).controls['text-input'], '歷史作品修改');
  assert.equal(saved(ui).theme, 'theme-xuan');
});

for (const first of ['styles', 'catalog']) test(`draft hydrates before ${first}-first async fonts without conversion or loss`, async t => {
  const resolve = {};
  const ui = await createFrontend({ setup: seed({version:1, style:'longcang', script:'simp', controls:{'text-input':'保留繁體鳥', 'inscription-input':''}}), fetch: ({url}) => {
    if (url === '/api/styles') return new Promise(done => resolve.styles = done);
    if (url === '/api/font-catalog') return new Promise(done => resolve.catalog = done);
  }}); t.after(ui.close);
  const data = {styles:jsonResponse({styles:[{id:'kai', name:'Kai'}]}), catalog:jsonResponse([{id:'longcang-xingshu',name_zh:'龍藏行書',char_support:'simp'}])};
  assert.equal(el(ui,'text-input').value,'保留繁體鳥');
  resolve[first](data[first]); await flush();
  edit(ui,'inscription-input','新落款'); assert.equal(saved(ui).style,'longcang');
  resolve[first === 'styles' ? 'catalog' : 'styles'](data[first === 'styles' ? 'catalog' : 'styles']); await flush();
  assert.equal(el(ui,'style-select').value,'longcang');
  assert.equal(el(ui,'text-input').value,'保留繁體鳥');
  assert.equal(el(ui,'btn-simp').getAttribute('aria-pressed'),'true');
  assert.equal(ui.requests.some(r=>r.url==='/api/convert-script'),false);
});

for (const value of ['{bad','null','[]','{"version":99,"controls":{"text-input":"wrong"}}', '{"version":1,"controls":{"text-input":{},"size-slider":"Infinity","fit-toggle":"false","paper-style-select":"bad"},"canvasWidth":-1,"theme":"bad","script":"bad"}']) test(`invalid draft is safe: ${value}`, async t => {
  const ui = await createFrontend({setup:seed(value)}); t.after(ui.close);
  assert.equal(el(ui,'text-input').value,'明月松間照\n清泉石上流');
  assert.equal(el(ui,'fit-toggle').checked,true);
  edit(ui,'text-input','新'); assert.equal(saved(ui).controls['text-input'],'新');
});

for (const mode of ['read','write']) test(`unavailable storage ${mode} leaves text and controls usable`, async t => {
  const ui = await createFrontend({setup(window) {
    if (mode==='read') Object.defineProperty(window,'localStorage',{get(){throw Error('denied');}});
    else window.Storage.prototype.setItem=()=>{throw Error('quota');};
  }}); t.after(ui.close);
  edit(ui,'text-input','仍可書寫'); edit(ui,'inscription-input',''); edit(ui,'spacing-slider','0.4');
  assert.equal(el(ui,'text-input').value,'仍可書寫');
  ui.window.dispatchEvent(new ui.window.Event('pagehide'));
});

test('unknown fields and capabilities are never copied into a draft', async t => {
  const ui = await createFrontend({setup:seed({version:1,token:'secret',controls:{'video-share-url':'secret','text-input':'草稿'}})}); t.after(ui.close);
  ui.window.sessionStorage.setItem('calligraphy-share:job','secret');
  edit(ui,'text-input','新草稿');
  assert.doesNotMatch(ui.window.localStorage.getItem(key),/secret|token|video-share/);
});

test('adopted history preserves valid non-preset settings on reload', async t => {
  const ui = await createFrontend({jobs:[{job_id:'custom', job_type:'render', status:'succeeded', text:'非預設', style:'kai',
    params:{font_size:155, spacing:1.25, speed:2.5, fps:48, width:800, height:1100}}]}); t.after(ui.close);
  ui.document.querySelector('[data-job-id="custom"] .job-text').click(); el(ui,'detail-reuse').click();
  edit(ui,'text-input','新非預設');
  const copy = await reload(ui,t);
  for (const [id,value] of [['size-slider','155'],['spacing-slider','1.25'],['speed-select','2.5'],['fps-select','48']]) assert.equal(el(copy,id).value,value);
  assert.equal(copy.document.querySelector('[data-speed="2.5"]').getAttribute('aria-pressed'),'true');
});

for (const value of ['null','{}','[null,{},"kai"]']) test(`malformed favorites remain safe: ${value}`, async t => {
  const ui = await createFrontend({setup(window){window.localStorage.setItem('calligraphy.favorites',value);}}); t.after(ui.close);
  el(ui,'font-current').click();
  assert.ok(ui.document.querySelector('.picker-item'));
});

test('explicit picker script conversion adopts replay but favorites and filters do not', async t => {
  const ui = await createFrontend({jobs:[{job_id:'convert',job_type:'render',status:'succeeded',style:'kai',text:'風',params:{}}],
    fetch:({url})=>url==='/api/convert-script'?jsonResponse({text:'风'}):undefined}); t.after(ui.close);
  edit(ui,'text-input','自己的草稿'); const before=saved(ui);
  ui.document.querySelector('[data-job-id="convert"] .job-text').click(); el(ui,'detail-reuse').click();
  el(ui,'font-current').click(); ui.document.querySelector('.picker-item .star').click();
  ui.document.querySelector('#picker-support [data-sup="all"]').click();
  ui.window.dispatchEvent(new ui.window.Event('pagehide')); assert.deepEqual(saved(ui),before);
  ui.document.querySelector('#picker-support [data-sup="simp"]').click(); await flush();
  assert.equal(saved(ui).controls['text-input'],'风'); assert.equal(saved(ui).script,'simp');
});
