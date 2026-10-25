import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush } from './helpers/frontend.mjs';

test('stamp drag handle bounds align exactly with X-Stamp-Bounds and snap to lane centers', async t => {
  const samplePng = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 10, 73, 68, 65, 84, 120, 156, 99, 0, 1, 0, 0, 5, 0, 1, 13, 10, 45, 180, 0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130]);

  const ui = await createFrontend({
    fetch: ({ url }) => {
      if (url === '/api/editor-preview') {
        const body = new Blob([samplePng], { type: 'image/png' });
        const headers = new Headers({
          'Content-Type': 'image/png',
          'X-Stamp-Bounds': '243,684,64,720,960',
          'X-Stamp-Grid': '20,40,700,919,56.67,12',
          'X-Stamp-Centers': '48.33,105.00,161.67,218.33,275.00,331.67,388.33,445.00,501.67,558.33,615.00,671.67',
          'X-Stamp-Enabled': '1',
        });
        return new Response(body, { status: 200, headers });
      }
    },
  });
  t.after(ui.close);
  const { document, window } = ui;
  const stage = document.getElementById('calligraphy-stage');
  const handle = document.getElementById('stamp-drag-handle');
  const posSelect = document.getElementById('stamp-position-select');

  assert.ok(stage && handle && posSelect);

  // Trigger preview update
  document.getElementById('text-input').value = '春江潮水連海平';
  document.getElementById('text-input').dispatchEvent(new window.Event('input', { bubbles: true }));
  await ui.tickTimeouts(800);
  await flush();

  // Handle must match the exact X-Stamp-Bounds percentages:
  // sx=243, cw=720 -> 243/720 = 33.75%
  // sy=684, ch=960 -> 684/960 = 71.25%
  // sz=64, cw=720 -> 64/720 = 8.89%
  // sz=64, ch=960 -> 64/960 = 6.67%
  assert.equal(handle.style.left, '33.75%');
  assert.equal(handle.style.top, '71.25%');
  assert.equal(handle.style.width, '8.89%');
  assert.equal(handle.style.height, '6.67%');
  assert.equal(handle.hidden, false);

  // Mock stage bounding rect: 360px wide, 480px tall, positioned at (0, 0)
  stage.getBoundingClientRect = () => ({
    left: 0,
    top: 0,
    width: 360,
    height: 480,
    right: 360,
    bottom: 480,
  });

  const PointerEvent = window.PointerEvent || class PointerEvent extends window.MouseEvent {
    constructor(type, props = {}) {
      super(type, props);
      this.pointerId = props.pointerId ?? 1;
    }
  };

  // Drag stamp to pointer clientX=52 (maps to 52 / 360 * 720 = 104 in canvas coordinates)
  // 104 is closest to lane center 105.00 (index 1)
  // clientY=240 (maps to 240 / 480 * 960 = 480 in canvas coordinates)
  handle.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0, clientX: 52, clientY: 240 }));
  await ui.tickTimeouts();

  window.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: 52, clientY: 240 }));

  // Dropdown switches to custom
  assert.equal(posSelect.value, 'custom');

  // Lane index 1 center is 105.00. sz=64 -> target sx = 105.00 - 32 = 73.
  // 73 / 720 = 10.14%
  assert.equal(handle.style.left, '10.14%');

  // End drag
  window.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
  await ui.tickTimeouts();
  await flush();

  // Subsequent request contains custom position and col=1
  const lastPreviewReq = ui.requests.filter(r => r.url === '/api/editor-preview').at(-1);
  assert.ok(lastPreviewReq);
  assert.equal(lastPreviewReq.body.stamp_position, 'custom');
  assert.equal(lastPreviewReq.body.stamp_col, 1);
});

test('horizontal-lr: stamp handle bounds align with response and snap to horizontal rows', async t => {
  const samplePng = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 10, 73, 68, 65, 84, 120, 156, 99, 0, 1, 0, 0, 5, 0, 1, 13, 10, 45, 180, 0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130]);

  const ui = await createFrontend({
    fetch: ({ url }) => {
      if (url === '/api/editor-preview') {
        const body = new Blob([samplePng], { type: 'image/png' });
        const headers = new Headers({
          'Content-Type': 'image/png',
          'X-Stamp-Bounds': '560,180,64,960,640',
          'X-Stamp-Grid': '40,20,919,620,68.00,8',
          'X-Stamp-Centers': '54.00,122.00,190.00,258.00,326.00,394.00,462.00,530.00',
          'X-Stamp-Enabled': '1',
        });
        return new Response(body, { status: 200, headers });
      }
    },
  });
  t.after(ui.close);
  const { document, window } = ui;
  const stage = document.getElementById('calligraphy-stage');
  const handle = document.getElementById('stamp-drag-handle');
  const posSelect = document.getElementById('stamp-position-select');

  document.getElementById('btn-horizontal').click();
  document.getElementById('text-input').value = '春江花月夜';
  document.getElementById('text-input').dispatchEvent(new window.Event('input', { bubbles: true }));
  await ui.tickTimeouts(800);
  await flush();

  // sx=560, cw=960 -> 560/960 = 58.33%
  // sy=180, ch=640 -> 180/640 = 28.13%
  // sz=64, cw=960 -> 64/960 = 6.67%
  // sz=64, ch=640 -> 64/640 = 10.00%
  assert.equal(handle.style.left, '58.33%');
  assert.equal(handle.style.top, '28.13%');
  assert.equal(handle.style.width, '6.67%');
  assert.equal(parseFloat(handle.style.height), 10);

  stage.getBoundingClientRect = () => ({
    left: 0,
    top: 0,
    width: 480,
    height: 320,
    right: 480,
    bottom: 320,
  });

  const PointerEvent = window.PointerEvent || class PointerEvent extends window.MouseEvent {
    constructor(type, props = {}) {
      super(type, props);
      this.pointerId = props.pointerId ?? 1;
    }
  };

  // Drag stamp to pointer clientY=95 (maps to 95 / 320 * 640 = 190 in canvas coordinates)
  // 190 is closest to row center 190.00 (index 2)
  handle.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0, clientX: 200, clientY: 95 }));
  await ui.tickTimeouts();

  window.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, clientX: 200, clientY: 95 }));

  assert.equal(posSelect.value, 'custom');
  // Row center 190.00 - 32 = 158. 158 / 640 = 24.69%
  assert.equal(handle.style.top, '24.69%');

  window.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
  await ui.tickTimeouts();
  await flush();

  const lastReq = ui.requests.filter(r => r.url === '/api/editor-preview').at(-1);
  assert.ok(lastReq);
  assert.equal(lastReq.body.stamp_position, 'custom');
  assert.equal(lastReq.body.stamp_col, 2);
});
