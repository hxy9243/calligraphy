import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const jobs = [
  {job_id:'video_one',job_type:'render',status:'succeeded',style:'kai',text:'永'},
  {job_id:'video_two',job_type:'render',status:'succeeded',style:'kai',text:'山'},
  {job_id:'queued',job_type:'render',status:'queued',style:'kai'},
  {job_id:'image',job_type:'preview',status:'succeeded',style:'kai'},
];
const link = {url:'/watch.html#video_one.'+'a'.repeat(43),expires_at: Date.now()/1000+3600};

test('history opens a work modal without leaving history and pauses/unloads on close', async t => {
  const ui = await createFrontend({jobs}); t.after(ui.close);
  const {document,window,mediaEvents} = ui;
  window.location.hash='#history'; window.dispatchEvent(new window.HashChangeEvent('hashchange')); await flush();
  const trigger=document.querySelector('.btn-play-mini'); trigger.focus(); trigger.click();
  const dialog=document.getElementById('job-detail');
  assert.equal(dialog.open,true); assert.equal(window.location.hash,'#history');
  assert.equal(document.getElementById('tab-result'),null);
  const video=dialog.querySelector('video');
  assert.equal(video.autoplay,false); assert.equal(video.controls,true);
  assert.equal(mediaEvents.some(e=>e.method==='play' && e.element===video),false);
  dialog.querySelector('[data-close]').click();
  assert.equal(dialog.open,false); assert.equal(video.hasAttribute('src'),false);
  assert.equal(document.activeElement,trigger);
  trigger.click();
  assert.notEqual(dialog.querySelector('video'),video);
  dialog.dispatchEvent(new window.Event('pointerdown',{bubbles:true})); dialog.click();
  assert.equal(dialog.open,false);
});

test('only completed videos offer explicit share creation, copy and revoke across reopen',async t=>{
  let copied;
  const ui=await createFrontend({jobs,setup(window){ Object.defineProperty(window.navigator,'clipboard',{value:{writeText:async value=>{copied=value;}}}); }, fetch({url,options}){if(url.endsWith('/share-link'))return jsonResponse(options.method==='DELETE'?{}:link);}});t.after(ui.close);
  const d=ui.document, byId=id=>d.getElementById('video-share-'+id);
  assert.equal(d.querySelectorAll('.btn-share-video').length,2);
  d.querySelector('.btn-share-video').click();
  assert.equal(byId('notice').open,true); assert.match(byId('notice').textContent,/任何持有連結的人/); assert.match(byId('notice').textContent,/72 小時/);
  assert.equal(ui.requests.some(r=>r.url.endsWith('/share-link')),false);
  byId('create').click();byId('create').click();await flush();
  assert.equal(ui.requests.filter(r=>r.url.endsWith('/share-link')).length,1);
  byId('copy').click();await flush();assert.equal(copied,'http://calligraphy.test'+link.url);
  assert.match(byId('status').textContent,/任何持有連結的人/); assert.match(byId('status').textContent,/有效至/);
  byId('notice').close();d.querySelector('.btn-share-video').click();
  assert.equal(byId('url').value,''); assert.equal(byId('revoke').hidden,false);
  byId('revoke').click();await flush();assert.match(byId('status').textContent,/已停用/);
});

test('closing pending share and switching videos ignores stale response and serializes mutations',async t=>{
  let finish;
  const ui=await createFrontend({jobs,fetch({url}){if(url.endsWith('/share-link'))return new Promise(resolve=>{finish=resolve;});}});t.after(ui.close);
  const d=ui.document, byId=id=>d.getElementById('video-share-'+id), buttons=d.querySelectorAll('.btn-share-video');
  buttons[0].click();byId('create').click();byId('notice').close();buttons[1].click();
  assert.equal(byId('create').disabled,true);byId('create').click();finish(jsonResponse(link));await flush();
  assert.equal(byId('url').value,'');assert.equal(byId('create').disabled,false);
  byId('create').click();finish(jsonResponse({url:'/watch.html#video_two.'+'b'.repeat(43),expires_at:link.expires_at}));await flush();
  byId('copy').click();await flush();assert.equal(byId('url').selectionEnd,byId('url').value.length);
  assert.match(byId('status').textContent,/長按/); assert.match(byId('status').textContent,/任何持有連結的人/); assert.match(byId('status').textContent,/有效至/);
});

test('modal keyboard wraps focus, Escape restores it, and route changes release video', async t=>{
  const ui=await createFrontend({jobs});t.after(ui.close);
  const {document:d,window:w}=ui;
  const trigger=d.querySelector('.btn-play-mini');trigger.focus();trigger.click();
  const dialog=d.getElementById('job-detail'), first=dialog.querySelector('[data-close]'),last=d.getElementById('detail-reuse');
  last.focus();last.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));
  assert.equal(d.activeElement,first);
  first.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));
  assert.equal(d.activeElement,last);
  last.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  assert.equal(dialog.open,false);assert.equal(d.activeElement,trigger);
  trigger.click();const video=dialog.querySelector('video');
  w.location.hash='#fonts';w.dispatchEvent(new w.HashChangeEvent('hashchange'));await flush();
  assert.equal(dialog.open,false);assert.equal(video.hasAttribute('src'),false);
});

test('viewport work media overrides legacy ID-selector height caps', async()=>{
  const {readFile}=await import('node:fs/promises');
  const css=await readFile(new URL('../frontend/style.css',import.meta.url),'utf8');
  assert.match(css,/\.work-dialog #detail-viewer, \.work-dialog \.export-output-box \{[^}]*min-height: 0;[^}]*max-height: none;/);
  assert.match(css,/\.work-dialog #detail-viewer > video[^}]*max-height: 100%;/);
  assert.match(css,/\.job-action \{ flex-wrap: wrap; \}/);
});

test('a late still preview cannot reopen a modal after newer navigation',async t=>{
  let finish;
  const ui=await createFrontend({jobs,fetch({url}){if(url==='/api/previews')return new Promise(resolve=>{finish=resolve;});}});t.after(ui.close);
  ui.document.getElementById('btn-preview').click();
  ui.window.location.hash='#history';ui.window.dispatchEvent(new ui.window.HashChangeEvent('hashchange'));await flush();
  finish(jsonResponse({svg:'<svg xmlns="http://www.w3.org/2000/svg"></svg>'}));await flush();
  assert.equal(ui.document.getElementById('result-dialog').open,false);
  assert.equal(ui.window.location.hash,'#history');
});
