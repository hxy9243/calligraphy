import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

async function setup(t) {
  const conversions = [];
  const ui = await createFrontend({
    fetch: ({ url, body }) => {
      if (url !== '/api/convert-script') return undefined;
      return new Promise((resolve, reject) => conversions.push({ body, resolve, reject }));
    },
  });
  t.after(ui.close);
  const input = ui.document.getElementById('text-input');
  const status = ui.document.getElementById('status-message');
  const setText = text => {
    input.value = text;
    input.dispatchEvent(new ui.window.Event('input', { bubbles: true }));
  };
  const click = id => ui.document.getElementById(id).click();
  return { ...ui, conversions, input, status, setText, click };
}

test('script conversion uses server results and the requested direction', async t => {
  const ui = await setup(t);
  ui.setText('鸟');
  ui.click('btn-trad');
  assert.deepEqual(ui.conversions[0].body, { text: '鸟', target: 'trad' });
  ui.conversions[0].resolve(jsonResponse({ text: '鳥', target: 'trad' }));
  await flush();
  assert.equal(ui.input.value, '鳥');
  assert.equal(ui.document.getElementById('calligraphy-text').textContent, '鳥');
  assert.equal(ui.document.getElementById('char-count').textContent, '1');
  assert.ok(ui.status.classList.contains('success'));

  ui.click('btn-simp');
  assert.deepEqual(ui.conversions[1].body, { text: '鳥', target: 'simp' });
  ui.conversions[1].resolve(jsonResponse({ text: '鸟', target: 'simp' }));
  await flush();
  assert.equal(ui.input.value, '鸟');
});

const failures = {
  unavailable: request => request.resolve(jsonResponse({ detail: 'zhconv unavailable' }, 503)),
  network: request => request.reject(new Error('Offline')),
  malformed: request => request.resolve(jsonResponse({ detail: 'Missing text' })),
};

for (const [reason, fail] of Object.entries(failures)) {
  test(`current ${reason} conversion uses an explicitly limited offline fallback`, async t => {
    const ui = await setup(t);
    ui.setText('鸟');
    ui.click('btn-trad');
    fail(ui.conversions[0]);
    await flush();
    assert.equal(ui.input.value, '鳥');
    assert.match(ui.status.textContent, /离线字表/);
    assert.match(ui.status.textContent, /部分字词可能未转换/);
    assert.ok(!ui.status.classList.contains('success'));
  });
}

test('an unchanged offline fallback is not presented as a successful full conversion', async t => {
  const ui = await setup(t);
  ui.setText('龟'); // Outside the bundled fallback dictionary.
  ui.click('btn-trad');
  failures.unavailable(ui.conversions[0]);
  await flush();
  assert.equal(ui.input.value, '龟');
  assert.match(ui.status.textContent, /部分字词可能未转换/);
  assert.ok(!ui.status.classList.contains('success'));
});

for (const [result, finish] of Object.entries({
  success: request => request.resolve(jsonResponse({ text: '鳥', target: 'trad' })),
  ...failures,
})) {
  test(`delayed ${result} conversion cannot overwrite a newer edit`, async t => {
    const ui = await setup(t);
    ui.setText('鸟');
    ui.click('btn-trad');
    ui.setText('新的文本');
    finish(ui.conversions[0]);
    await flush();
    assert.equal(ui.input.value, '新的文本');
    assert.equal(ui.document.getElementById('calligraphy-text').textContent, '新的文本');
    assert.ok(ui.status.classList.contains('hidden'));
  });

  test(`out-of-order ${result} cannot overwrite a newer conversion choice`, async t => {
    const ui = await setup(t);
    ui.setText('鸟');
    ui.click('btn-trad');
    ui.click('btn-simp');
    ui.conversions[1].resolve(jsonResponse({ text: '鸟', target: 'simp' }));
    await flush();
    const latestStatus = ui.status.textContent;
    finish(ui.conversions[0]);
    await flush();
    assert.equal(ui.input.value, '鸟');
    assert.ok(ui.document.getElementById('btn-simp').classList.contains('active'));
    assert.equal(ui.status.textContent, latestStatus);
  });

  test(`delayed ${result} conversion cannot replace a newly selected preset`, async t => {
    const ui = await setup(t);
    ui.setText('鸟');
    ui.click('btn-trad');
    ui.document.querySelector('.preset-btn').click();
    const presetText = ui.input.value;
    finish(ui.conversions[0]);
    await flush();
    assert.equal(ui.input.value, presetText);
    assert.equal(ui.document.getElementById('calligraphy-text').textContent, presetText);
    assert.ok(ui.status.classList.contains('hidden'));
  });
}

test('editing then restoring the original text still invalidates a pending conversion', async t => {
  const ui = await setup(t);
  ui.setText('鸟');
  ui.click('btn-trad');
  ui.setText('新稿');
  ui.setText('鸟');
  ui.conversions[0].resolve(jsonResponse({ text: '鳥' }));
  await flush();
  assert.equal(ui.input.value, '鸟');
});

test('choosing a preset with the same text still invalidates a pending conversion', async t => {
  const ui = await setup(t);
  ui.setText('明月松間照\n清泉石上流');
  ui.click('btn-trad');
  ui.document.querySelector('.preset-btn').click();
  ui.conversions[0].resolve(jsonResponse({ text: '过时的响应' }));
  await flush();
  assert.equal(ui.input.value, '明月松間照\n清泉石上流');
});

test('responses waiting on JSON parsing cannot overwrite a later edit', async t => {
  const ui = await setup(t);
  let resolveBody;
  ui.setText('鸟');
  ui.click('btn-trad');
  ui.conversions[0].resolve({ ok: true, json: () => new Promise(resolve => { resolveBody = resolve; }) });
  await flush();
  ui.setText('修改后');
  resolveBody({ text: '鳥' });
  await flush();
  assert.equal(ui.input.value, '修改后');
});

test('repeated conversion-toggle clicks use the latest pending direction', async t => {
  const ui = await setup(t);
  ui.setText('鸟');
  ui.click('btn-convert-current');
  ui.click('btn-convert-current');
  assert.deepEqual(ui.conversions.map(request => request.body.target), ['trad', 'simp']);
  ui.conversions[0].resolve(jsonResponse({ text: '鳥' }));
  await flush();
  assert.equal(ui.input.value, '鸟');
  assert.match(ui.status.textContent, /正在转换文本为简体/);
  ui.conversions[1].resolve(jsonResponse({ text: '鸟' }));
  await flush();
  assert.equal(ui.input.value, '鸟');
});

test('a new script choice for empty text supersedes an older request', async t => {
  const ui = await setup(t);
  ui.setText('鸟');
  ui.click('btn-trad');
  ui.setText('');
  ui.click('btn-simp');
  assert.equal(ui.conversions.length, 1);
  ui.conversions[0].resolve(jsonResponse({ text: '鳥' }));
  await flush();
  assert.equal(ui.input.value, '');
  assert.ok(ui.document.getElementById('btn-simp').classList.contains('active'));
});

test('font-driven conversion choices supersede a pending conversion', async t => {
  const ui = await setup(t);
  const style = ui.document.getElementById('style-select');
  const selectFont = id => {
    style.appendChild(new ui.window.Option(id, id));
    style.value = id;
    style.dispatchEvent(new ui.window.Event('change'));
  };
  ui.setText('鸟');
  selectFont('i-yan-kai');
  selectFont('mashanzheng');
  assert.deepEqual(ui.conversions.map(request => request.body.target), ['trad', 'simp']);
  ui.conversions[1].resolve(jsonResponse({ text: '鸟' }));
  ui.conversions[0].resolve(jsonResponse({ text: '鳥' }));
  await flush();
  assert.equal(ui.input.value, '鸟');
  assert.ok(ui.document.getElementById('btn-simp').classList.contains('active'));
});

test('an older success timer cannot hide a newer conversion status', async t => {
  const ui = await setup(t);
  ui.setText('鸟');
  ui.click('btn-trad');
  ui.conversions[0].resolve(jsonResponse({ text: '鳥' }));
  await flush();
  ui.click('btn-simp');
  await ui.tickTimeouts();
  assert.match(ui.status.textContent, /正在转换文本为简体/);
  assert.ok(!ui.status.classList.contains('hidden'));
  ui.conversions[1].resolve(jsonResponse({ text: '鸟' }));
  await flush();
});
