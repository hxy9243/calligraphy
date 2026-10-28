import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

test('custom ruling count preserves input and matches editor, still and video requests', async t => {
  const ui = await createFrontend({ fetch: ({ url }) => {
    if (url === '/api/previews') return jsonResponse({ svg: '<svg viewBox="0 0 100 100"></svg>' });
    if (url === '/api/renders') return jsonResponse({ job_id: 'video', status: 'queued' }, 202);
  }});
  t.after(ui.close);
  const { document: d, window: w } = ui;
  const text = d.getElementById('text-input').value;
  d.querySelector('[data-cf="custom"]').click();
  const count = d.getElementById('paper-lines');
  assert.equal(d.getElementById('paper-lines-field').hidden, false);
  const selectedCount = Number(count.min) + 4;
  count.value = String(selectedCount); count.dispatchEvent(new w.Event('input'));
  await ui.tickTimeouts(800);
  d.getElementById('btn-preview').click(); await flush();
  d.getElementById('btn-render').click(); await flush();
  for (const url of ['/api/editor-preview', '/api/previews', '/api/renders']) {
    const body = ui.requests.filter(r => r.url === url).at(-1).body;
    assert.equal(body.paper_line_count, selectedCount);
    assert.equal(body.text, text);
  }
  d.getElementById('btn-horizontal').click();
  assert.equal(d.querySelector('label[for="paper-lines"]').textContent, '箋紙行數');
  d.querySelector('[data-cf="auto"]').click();
  await ui.tickTimeouts(800);
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body.paper_line_count, undefined);
  assert.equal(d.getElementById('text-input').value, text);
});

test('wheel and pinch zoom only artwork, are bounded and do not re-render', async t => {
  const ui = await createFrontend(); t.after(ui.close);
  const { document: d, window: w } = ui;
  await ui.tickTimeouts(800);
  const count = ui.requests.length;
  const viewport = d.getElementById('stage-viewport');
  const stage = d.getElementById('calligraphy-stage');
  const scroll = new w.WheelEvent('wheel', {deltaY: 100, cancelable: true});
  viewport.dispatchEvent(scroll);
  assert.equal(scroll.defaultPrevented, false);
  assert.equal(stage.style.zoom || '', '');
  const wheel = new w.WheelEvent('wheel', {deltaY: -100, ctrlKey: true, bubbles: true, cancelable: true});
  viewport.dispatchEvent(wheel);
  assert.equal(wheel.defaultPrevented, true);
  assert.ok(Number(stage.style.zoom) > 1);
  assert.equal(d.body.style.zoom || '', '');
  assert.equal(ui.requests.length, count);
  for (let i = 0; i < 30; i++) viewport.dispatchEvent(new w.WheelEvent('wheel', {deltaY: -200, ctrlKey: true, cancelable: true}));
  assert.equal(Number(stage.style.zoom), 3);
  d.getElementById('preview-zoom-reset').click();
  assert.equal(Number(stage.style.zoom), 1);
  const outside = new w.WheelEvent('wheel', {deltaY: -100, cancelable: true});
  d.getElementById('text-input').dispatchEvent(outside);
  assert.equal(outside.defaultPrevented, false);
});

test('editor overlay covers an existing image and clears after success or failure', async t => {
  let release;
  let block = false;
  const ui = await createFrontend({fetch: ({url}) => {
    if (url === '/api/editor-preview' && block) return new Promise(resolve => { release = resolve; });
  }}); t.after(ui.close);
  await ui.tickTimeouts(800);
  const {document: d, window: w} = ui;
  assert.equal(d.getElementById('editor-preview').hidden, false);
  for (const ok of [true, false]) {
    block = true;
    d.getElementById('text-input').dispatchEvent(new w.Event('input'));
    const pending = ui.tickTimeouts(800); await flush();
    assert.equal(d.getElementById('preview-render-overlay').hidden, false);
    assert.equal(d.getElementById('stage-viewport').getAttribute('aria-busy'), 'true');
    release(ok ? {ok: true, blob: async () => new w.Blob(['png'])} : jsonResponse({detail:'Render failed'},422));
    await pending;
    assert.equal(d.getElementById('preview-render-overlay').hidden, true);
  }
  assert.equal(d.getElementById('editor-preview-status').hidden, false);
});

test('background video queue polling never covers the live preview', async t => {
  let jobs = [];
  const ui = await createFrontend({fetch: ({url}) => {
    if (url === '/api/renders') { jobs = [{job_id:'video',status:'queued',job_type:'render',text:'永',params:{}}]; return jsonResponse({job_id:'video'},202); }
    if (url === '/api/jobs') return jsonResponse({jobs});
  }}); t.after(ui.close);
  await ui.tickTimeouts(800);
  ui.document.getElementById('btn-render').click(); await flush();
  await ui.tickTimeouts(800);
  assert.equal(ui.document.getElementById('preview-render-overlay').hidden, true);
  jobs = [{...jobs[0],status:'running',progress:.5}];
  await ui.tickTimeouts(1000);
  assert.equal(ui.document.getElementById('preview-render-overlay').hidden, true);
  jobs = [{...jobs[0],status:'failed',error_message:'Fixture failure'}];
  await ui.tickTimeouts(1000);
  assert.equal(ui.document.getElementById('preview-render-overlay').hidden, true);
});

test('exported SVG wheel zoom leaves the dialog and download content unchanged', async t => {
  const ui = await createFrontend({fetch: ({url}) => {
    if (url === '/api/previews') return jsonResponse({svg:'<svg viewBox="0 0 200 300"><path d="M0 0L100 100"/></svg>'});
  }}); t.after(ui.close);
  const {document:d,window:w} = ui;
  d.getElementById('btn-preview').click(); await flush();
  const svg = d.querySelector('#preview-svg-container svg');
  const link = d.getElementById('result-download').href;
  const wheel = new w.WheelEvent('wheel',{deltaY:-100,ctrlKey:true,cancelable:true,bubbles:true});
  svg.dispatchEvent(wheel);
  assert.equal(wheel.defaultPrevented,true);
  assert.ok(Number(svg.style.zoom)>1);
  assert.equal(d.querySelector('.work-dialog').style.zoom || '', '');
  assert.equal(d.getElementById('result-download').href,link);
  d.getElementById('result-zoom').click();
  assert.equal(Number(svg.style.zoom),1);
});


test('paper slider follows rendered line count and presets are expanded', async t => {
  const ui = await createFrontend(); t.after(ui.close);
  const {document:d, window:w} = ui;
  assert.equal(d.querySelector('.presets-block').open, true);
  d.querySelector('[data-cf="custom"]').click();
  const text = d.getElementById('text-input');
  const inscription = d.getElementById('inscription-input');
  inscription.value = '';
  const slider = d.getElementById('paper-lines');
  for (const [value, minimum] of [['明月\n清泉',2], ['明月\n清泉\n松間',3]]) {
    text.value = value; text.dispatchEvent(new w.Event('input'));
    assert.equal(slider.min, String(minimum));
    assert.equal(slider.step, '2');
    slider.value = '32'; slider.dispatchEvent(new w.Event('input'));
    assert.equal(Number(slider.value), minimum === 2 ? 32 : 31);
  }
  text.value = Array(33).fill('永').join('\n'); text.dispatchEvent(new w.Event('input'));
  assert.equal(slider.disabled, true);
});

test('layered stamp follows pointer immediately without requesting another render', async t => {
  const headers = new Map([
    ['Content-Type','application/json'], ['X-Stamp-Bounds','30,50,40,480,640'],
    ['X-Stamp-Grid','20,20,460,620,110,4'], ['X-Stamp-Centers','75,185,295,405'], ['X-Stamp-Enabled','1'],
  ]);
  const ui = await createFrontend({fetch: ({url}) => {
    if (url === '/api/editor-preview') return {...jsonResponse({image:'cG5n',stamp:'c3RhbXA='}), headers: {get: key => headers.get(key)}};
    if (url === '/api/previews') return jsonResponse({svg:'<svg></svg>'});
  }}); t.after(ui.close);
  await ui.tickTimeouts(800);
  const {document:d, window:w} = ui;
  const stage = d.getElementById('calligraphy-stage');
  stage.getBoundingClientRect = () => ({left:0,top:0,width:480,height:640});
  const stamp = d.getElementById('stamp-preview');
  const handle = d.getElementById('stamp-drag-handle');
  assert.equal(stamp.hidden, false);
  const before = stamp.style.top;
  const requests = ui.requests.filter(r => r.url === '/api/editor-preview').length;
  const pointer = (target, name, x, y) => {
    const event = new w.Event(name, {bubbles:true,cancelable:true});
    Object.assign(event, {clientX:x,clientY:y,pointerId:1,button:0}); target.dispatchEvent(event);
  };
  pointer(handle,'pointerdown',50,70); await ui.tickTimeouts(80);
  pointer(w,'pointermove',300,400); pointer(w,'pointerup',300,400);
  assert.notEqual(stamp.style.top, before);
  assert.equal(stamp.style.top, handle.style.top);
  await ui.tickTimeouts(0);
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').length, requests);
  d.getElementById('btn-preview').click(); await flush();
  const body = ui.requests.find(r => r.url === '/api/previews').body;
  assert.equal(body.stamp_position, 'custom');
  assert.ok(body.stamp_row > 0);
});


for (const [button, endpoint, result] of [
  ['btn-preview','/api/previews',{svg:'<svg></svg>'}],
  ['btn-render','/api/renders',{job_id:'background',status:'queued'}],
]) {
  test(`${endpoint} stays in the background and cannot clear an active editor overlay`, async t => {
    let finishExport, finishEditor, blockEditor = false;
    const ui = await createFrontend({fetch: ({url}) => {
      if (url === endpoint) return new Promise(resolve => { finishExport = resolve; });
      if (url === '/api/editor-preview' && blockEditor) return new Promise(resolve => { finishEditor = resolve; });
    }}); t.after(ui.close);
    await ui.tickTimeouts(800);
    const {document:d, window:w} = ui;
    const overlay = d.getElementById('preview-render-overlay');
    const before = ui.requests.filter(r => r.url === '/api/editor-preview').length;
    d.getElementById(button).click(); await flush();
    await ui.tickTimeouts(800);
    assert.equal(overlay.hidden, true);
    assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').length, before,
      'export validation must not start an editor render');
    assert.equal(d.getElementById('text-input').disabled, false);
    blockEditor = true;
    d.getElementById('text-input').dispatchEvent(new w.Event('input'));
    const pending = ui.tickTimeouts(800); await flush();
    assert.equal(overlay.hidden, false);
    finishExport(jsonResponse(result)); await flush();
    assert.equal(overlay.hidden, false, 'export completion must not clear the editor overlay');
    finishEditor({ok:true,blob:async()=>new w.Blob(['png'])}); await pending;
    assert.equal(overlay.hidden, true);
  });
}

test('preview quality changes only editor resolution; SVG quality stays automatic', async t => {
  const ui = await createFrontend({fetch: ({url}) => {
    if (url === '/api/previews') return jsonResponse({svg: '<svg viewBox="0 0 320 480"></svg>'});
    if (url === '/api/renders') return jsonResponse({job_id:'quality-video',status:'queued'},202);
  }}); t.after(ui.close);
  const {document:d, window:w} = ui;
  await ui.tickTimeouts(800);
  const baseline = ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body;
  assert.equal(baseline.preview_scale, 1);
  for (const scale of [2, 4, 1]) {
    const select = d.getElementById('preview-quality');
    select.value = String(scale); select.dispatchEvent(new w.Event('change'));
    await ui.tickTimeouts(0);
    const editor = ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body;
    assert.deepEqual(editor, {...baseline, preview_scale:scale});
    d.getElementById('btn-preview').click(); await flush();
    const still = ui.requests.filter(r => r.url === '/api/previews').at(-1).body;
    assert.equal(still.preview_scale, undefined);
    assert.equal(still.width, baseline.width);
    assert.equal(still.font_size, baseline.font_size);
  }
  d.getElementById('btn-render').click(); await flush();
  assert.equal(ui.requests.filter(r => r.url === '/api/renders').at(-1).body.preview_scale, undefined);
});

test('oversized high-quality preview shows actionable API validation errors', async t => {
  const message = 'Lower preview quality or canvas size';
  const ui = await createFrontend({fetch: ({url}) => {
    if (url === '/api/editor-preview' || url === '/api/previews')
      return jsonResponse({detail:[{msg:message}]},422);
  }}); t.after(ui.close);
  await ui.tickTimeouts(800);
  assert.match(ui.document.getElementById('editor-preview-status').textContent, /Lower preview quality/);
  ui.document.getElementById('btn-preview').click(); await flush();
  assert.ok(ui.document.body.textContent.includes(message));
  assert.ok(!ui.document.body.textContent.includes('[object Object]'));
});
