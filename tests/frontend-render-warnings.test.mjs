import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const warning='部分細小筆畫使用推估筆路；請檢視成品。';
const job=(job_id,warning_message)=>({job_id,warning_message,job_type:'render',status:'succeeded',text:'十',style:'kai'});

test('successful inferred jobs display a nonblocking caveat in history and details, including reload',async t=>{
  for(let load=0;load<2;load++){
    const ui=await createFrontend({jobs:[job('inferred',warning),job('normal',null)]});t.after(ui.close);
    const d=ui.document,card=d.querySelector('[data-job-id="inferred"]');
    assert.equal(card.querySelector('.job-warning').textContent,warning);
    assert.match(card.querySelector('.job-status-badge').textContent,/完成/);
    assert.ok(card.querySelector('.btn-download'));
    assert.equal(d.querySelector('[data-job-id="normal"] .job-warning'),null);
    card.querySelector('.btn-play-mini').click();
    assert.equal(d.querySelector('#detail-meta .job-warning').textContent,warning);
    assert.equal(d.getElementById('detail-download').hidden,false);
    d.getElementById('job-detail').close();
    d.querySelector('[data-job-id="normal"] .btn-play-mini').click();
    assert.equal(d.querySelector('#detail-meta .job-warning'),null);
  }
});

test('render caveats are escaped and never interpreted as markup',async t=>{
  const ui=await createFrontend({jobs:[job('one','<img src=x onerror=alert(1)>')]});t.after(ui.close);
  const d=ui.document;
  assert.equal(d.querySelector('.job-warning img'),null);
  assert.equal(d.querySelector('.job-warning').textContent,'<img src=x onerror=alert(1)>');
  d.querySelector('.btn-play-mini').click();
  assert.equal(d.querySelector('#detail-meta .job-warning img'),null);
});


test('still completion keeps its caveat visible until dismissal and clears it for a normal result',async t=>{
  let flagged=true;
  const ui=await createFrontend({fetch({url}){if(url==='/api/previews')return jsonResponse({svg:'<svg xmlns="http://www.w3.org/2000/svg"></svg>',warning_message:flagged?warning:null});}});t.after(ui.close);
  const d=ui.document,notice=d.getElementById('result-warning');
  d.getElementById('btn-preview').click();await flush();
  assert.equal(notice.hidden,false);assert.equal(notice.textContent,warning);
  assert.equal(d.getElementById('result-download').hidden,false);
  await ui.tickTimeouts(3000);assert.equal(notice.hidden,false);
  d.getElementById('result-dialog').close();assert.equal(notice.hidden,true);
  flagged=false;d.getElementById('btn-preview').click();await flush();
  assert.equal(d.getElementById('result-dialog').open,true);
  assert.equal(notice.hidden,true);assert.equal(notice.textContent,'');
});
