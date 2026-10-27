import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const byId = (ui, id) => ui.document.getElementById(id);
function change(ui, id, value) {
  byId(ui, id).value = value;
  byId(ui, id).dispatchEvent(new ui.window.Event('change'));
}
const responses = ({ url }) => {
  if (url === '/api/previews') return jsonResponse({ preview_url: '/fixtures/paper.png' });
  if (url === '/api/renders') return jsonResponse({ job_id: 'paper', status: 'queued' }, 202);
};

test('sidebar paper settings reach preview, still and video; decoration starts off', async t => {
  const ui = await createFrontend({ fetch: responses });
  t.after(ui.close);
  assert.equal(ui.document.querySelector('.topbar #theme-select'), null);
  assert.ok(byId(ui, 'card-paper').contains(byId(ui, 'theme-select')));
  assert.match(ui.document.title, /墨韵书法工坊/);
  assert.equal(byId(ui, 'paper-decoration-select').value, 'none');
  await ui.tickTimeouts(800);
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body.paper_decoration, undefined);
  change(ui, 'theme-select', 'theme-rubbing');
  change(ui, 'paper-tone-select', 'cool');
  change(ui, 'paper-style-select', 'silver');
  change(ui, 'paper-decoration-select', 'bamboo');
  await ui.tickTimeouts();
  byId(ui, 'btn-preview').click(); await flush();
  byId(ui, 'btn-render').click(); await flush();
  for (const endpoint of ['/api/editor-preview', '/api/previews', '/api/renders']) {
    const body = ui.requests.filter(r => r.url === endpoint).at(-1).body;
    for (const [key, value] of Object.entries({palette: 'dark', paper_tone: 'cool', paper_style: 'silver', paper_decoration: 'bamboo'})) {
      assert.equal(body[key], value, `${endpoint}: ${key}`);
    }
  }
  change(ui, 'paper-decoration-select', 'none');
  await ui.tickTimeouts();
  assert.equal(ui.requests.filter(r => r.url === '/api/editor-preview').at(-1).body.paper_decoration, undefined);
  change(ui, 'theme-select', 'theme-gold');
  assert.equal(byId(ui, 'paper-style-select').value, 'gold');
});

test('history restores paper choices and resets decoration for a legacy work', async t => {
  const params = {width: 720, height: 960, font_size: 68, palette: 'dark', paper_tone: 'warm', paper_style: 'mottled', paper_decoration: 'plum'};
  const jobs = [{job_id: 'decorated', params}, {job_id: 'legacy', params: {font_size: 68}}].map(job => ({...job, text: '永', style: 'kai', status: 'succeeded', job_type: 'render'}));
  const ui = await createFrontend({ jobs }); t.after(ui.close);
  for (const id of ['decorated', 'legacy']) {
    ui.document.querySelector(`[data-job-id="${id}"] .job-text`).click();
    byId(ui, 'detail-reuse').click(); await flush();
    assert.equal(byId(ui, 'paper-decoration-select').value, id === 'decorated' ? 'plum' : 'none');
    assert.equal(byId(ui, 'paper-tone-select').value, id === 'decorated' ? 'warm' : 'default');
    assert.equal(byId(ui, 'paper-style-select').value, id === 'decorated' ? 'mottled' : 'xuan');
  }
});
