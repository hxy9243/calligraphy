import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const job = { job_id: 'old', job_type: 'preview', status: 'succeeded', text: '永', style: 'kai' };
const setup = window => {
  window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  window.HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new window.Event('close'));
  };
};

test('history deletion requires confirmation, supports cancel and retry, and updates history', async t => {
  let jobs = [job, { ...job, job_id: 'active', status: 'rendering' }];
  let fail = true;
  const ui = await createFrontend({ setup, fetch: ({ url, options }) => {
    if (url === '/api/jobs') return jsonResponse({ jobs });
    if (options.method === 'DELETE') {
      if (fail) return jsonResponse({ detail: '请重试' }, 500);
      jobs = jobs.filter(j => j.job_id !== 'old');
      return jsonResponse(null, 204);
    }
  } });
  t.after(ui.close);
  const { document, requests } = ui;
  const dialog = document.getElementById('delete-history');
  const confirm = document.getElementById('confirm-delete-history');
  const deletes = () => requests.filter(r => r.options.method === 'DELETE');
  const open = () => document.querySelector('[data-job-id="old"] .btn-delete-history').click();
  assert.equal(document.querySelector('[data-job-id="active"] .btn-delete-history').disabled, true);
  open();
  assert.equal(dialog.open, true);
  assert.equal(document.getElementById('job-detail').open, false);
  assert.equal(deletes().length, 0);
  dialog.querySelector('button[data-close]').click();
  confirm.click();
  await flush();
  assert.equal(deletes().length, 0);
  open();
  confirm.click();
  confirm.click();
  await flush();
  assert.equal(deletes().length, 1);
  assert.equal(dialog.open, true);
  assert.equal(document.getElementById('delete-history-error').textContent, '请重试');
  assert.ok(document.querySelector('[data-job-id="old"]'));
  fail = false;
  confirm.click();
  await flush();
  assert.equal(dialog.open, false);
  assert.equal(document.querySelector('[data-job-id="old"]'), null);
  assert.ok(document.querySelector('[data-job-id="active"]'));
});

test('a list response started before deletion cannot resurrect a deleted card', async t => {
  let listCalls = 0;
  let staleResolve;
  const ui = await createFrontend({ setup, fetch: ({ url, options }) => {
    if (url === '/api/jobs') {
      listCalls++;
      if (listCalls === 1) return jsonResponse({ jobs: [job] });
      if (listCalls === 2) return new Promise(resolve => { staleResolve = resolve; });
      return jsonResponse({ jobs: [] });
    }
    if (options.method === 'DELETE') return jsonResponse(null, 204);
  } });
  t.after(ui.close);
  ui.window.location.hash = '#history';
  ui.window.dispatchEvent(new ui.window.Event('hashchange'));
  // Resolve an extra native hashchange deterministically before issuing deletion.
  await flush();
  ui.document.querySelector('.btn-delete-history').click();
  ui.document.getElementById('confirm-delete-history').click();
  await flush();
  staleResolve(jsonResponse({ jobs: [job] }));
  await flush();
  assert.equal(ui.document.querySelector('[data-job-id="old"]'), null);
  assert.equal(ui.document.querySelector('[data-history-count]').hidden, true);
});
