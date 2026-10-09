import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend } from './helpers/frontend.mjs';

export function setupDialogs(window) {
  window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  window.HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new window.Event('close'));
  };
}

test('font and playback dialogs dismiss outside, keep inside clicks, and pause playback', async t => {
  const ui = await createFrontend({ setup: setupDialogs, jobs: [{
    job_id: 'video', job_type: 'render', status: 'succeeded', style: 'kai', text: '永',
  }] });
  t.after(ui.close);
  const { document, window } = ui;
  document.getElementById('font-current').click();
  document.querySelector('.job-thumb').click();
  for (const id of ['font-picker', 'job-detail']) {
    const dialog = document.getElementById(id);
    assert.equal(dialog.open, true);
    dialog.querySelector('.sheet-inner').click();
    assert.equal(dialog.open, true);
    // A drag from content to the outside must not dismiss.
    dialog.querySelector('.sheet-inner').dispatchEvent(new window.Event('pointerdown', { bubbles: true }));
    dialog.click();
    assert.equal(dialog.open, true);
    dialog.dispatchEvent(new window.Event('pointerdown', { bubbles: true }));
    dialog.click();
    assert.equal(dialog.open, false);
  }
  assert.ok(ui.mediaEvents.some(e => e.method === 'pause' && e.element.tagName === 'VIDEO'));
});
