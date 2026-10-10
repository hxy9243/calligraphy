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

test('existing shares survive reopen and reload without rotating or extending their lifetime',async t=>{
  let copied, active = false, storage;
  const fetch=({url,options,body})=>{
    if(url.endsWith('/share-link/status')) return jsonResponse(active ? {active:true,...(body.token ? link : {expires_at:link.expires_at})} : {active:false});
    if(url.endsWith('/share-link')) {active=options.method!=='DELETE';return jsonResponse(active?link:{});}
  };
  const ui=await createFrontend({jobs,setup(window){Object.defineProperty(window.navigator,'clipboard',{value:{writeText:async value=>{copied=value;}}});},fetch});t.after(ui.close);
  const d=ui.document, byId=id=>d.getElementById('video-share-'+id);
  assert.equal(d.querySelectorAll('.btn-share-video').length,2);
  d.querySelector('.btn-share-video').click();await flush();
  assert.equal(byId('notice').open,true);assert.match(byId('notice').textContent,/72 小時/);
  assert.equal(ui.requests.some(r=>r.url.endsWith('/share-link')),false);
  byId('create').click();byId('create').click();await flush();
  assert.equal(ui.requests.filter(r=>r.url.endsWith('/share-link')).length,1);
  assert.equal(ui.requests.find(r=>r.url.endsWith('/share-link')).body.replace,false);
  byId('copy').click();await flush();assert.equal(copied,'http://calligraphy.test'+link.url);
  byId('notice').close();d.querySelector('.btn-share-video').click();
  assert.equal(byId('url').value,''); // Never expose cached bearer before owner validation.
  await flush();assert.equal(byId('url').value,copied);
  assert.match(byId('create').textContent,/取代舊連結/);
  assert.match(byId('status').textContent,/不會延長/);
  assert.equal(ui.requests.filter(r=>r.url.endsWith('/share-link')).length,1);
  storage=ui.window.sessionStorage.getItem('calligraphy-share:video_one');
  const reloaded=await createFrontend({jobs,fetch,setup(w){w.sessionStorage.setItem('calligraphy-share:video_one',storage);}});t.after(reloaded.close);
  reloaded.document.querySelector('.btn-share-video').click();await flush();
  assert.equal(reloaded.document.getElementById('video-share-url').value,copied);
  assert.equal(reloaded.requests.some(r=>r.url.endsWith('/share-link')),false);
  byId('revoke').click();await flush();assert.match(byId('status').textContent,/已停用/);
  assert.equal(ui.window.sessionStorage.getItem('calligraphy-share:video_one'),null);
});

test('an active share without a cached token requires explicit replacement and explains old-link invalidation',async t=>{
  const ui=await createFrontend({jobs,fetch({url}){if(url.endsWith('/share-link/status'))return jsonResponse({active:true,expires_at:link.expires_at});if(url.endsWith('/share-link'))return jsonResponse(link);}});t.after(ui.close);
  const d=ui.document;d.querySelector('.btn-share-video').click();await flush();
  assert.equal(d.getElementById('video-share-copy').hidden,true);
  assert.match(d.getElementById('video-share-status').textContent,/舊連結會立即失效/);
  d.getElementById('video-share-create').click();await flush();
  assert.equal(ui.requests.find(r=>r.url.endsWith('/share-link')).body.replace,true);
});

test('closing pending share creation still preserves its token, and switching videos ignores stale presentation',async t=>{
  let finish, active=false;
  const ui=await createFrontend({jobs,fetch({url,body}){
    if(url.endsWith('/share-link/status'))return jsonResponse(url.includes('video_one')&&active?{active:true,...(body.token?link:{expires_at:link.expires_at})}:{active:false});
    if(url.endsWith('/share-link'))return new Promise(resolve=>{finish=value=>{active=true;resolve(value);};});
  }});t.after(ui.close);
  const d=ui.document, byId=id=>d.getElementById('video-share-'+id), buttons=d.querySelectorAll('.btn-share-video');
  buttons[0].click();await flush();byId('create').click();byId('notice').close();buttons[1].click();await flush();
  assert.equal(byId('create').disabled,true);finish(jsonResponse(link));await flush();await flush();
  assert.equal(byId('url').value,'');assert.equal(byId('create').disabled,false);
  byId('notice').close();buttons[0].click();await flush();
  assert.equal(byId('url').value,'http://calligraphy.test'+link.url);
  byId('copy').click();await flush();assert.equal(byId('url').selectionEnd,byId('url').value.length);
  assert.match(byId('status').textContent,/長按/);
});

test('denied session storage degrades to in-memory reuse and stale-owner cache is never shown',async t=>{
  let active=false;
  const ui=await createFrontend({jobs,setup(w){Object.defineProperty(w,'sessionStorage',{get(){throw new Error('denied');}});},fetch({url}){
    if(url.endsWith('/share-link/status'))return jsonResponse(active?{active:true,...link}:{active:false});
    if(url.endsWith('/share-link')){active=true;return jsonResponse(link);}
  }});t.after(ui.close);
  const d=ui.document;d.querySelector('.btn-share-video').click();await flush();d.getElementById('video-share-create').click();await flush();
  d.getElementById('video-share-notice').close();d.querySelector('.btn-share-video').click();await flush();
  assert.equal(d.getElementById('video-share-url').value,'http://calligraphy.test'+link.url);
  const denied=await createFrontend({jobs,setup(w){w.sessionStorage.setItem('calligraphy-share:video_one',JSON.stringify(link));},fetch({url}){if(url.endsWith('/share-link/status'))return jsonResponse({},404);}});t.after(denied.close);
  denied.document.querySelector('.btn-share-video').click();await flush();
  assert.equal(denied.document.getElementById('video-share-url').value,'');
  assert.equal(denied.document.getElementById('video-share-create').disabled,true);
  assert.equal(denied.window.sessionStorage.getItem('calligraphy-share:video_one'),null);
});

test('copy revalidates after replacement/revocation elsewhere and fails closed on network errors',async t=>{
  let state={active:true,...link},copied=[];
  const ui=await createFrontend({jobs,setup(w){w.sessionStorage.setItem('calligraphy-share:video_one',JSON.stringify(link));Object.defineProperty(w.navigator,'clipboard',{value:{writeText:async value=>copied.push(value)}});},fetch({url}){
    if(url.endsWith('/share-link/status')) {if(state===null)throw new Error('offline');return jsonResponse(state);}
  }});t.after(ui.close);
  const d=ui.document,open=async()=>{d.querySelector('.btn-share-video').click();await flush();};
  await open();state={active:true,expires_at:link.expires_at};d.getElementById('video-share-copy').click();await flush();
  assert.deepEqual(copied,[]);assert.equal(d.getElementById('video-share-url').value,'');
  assert.equal(ui.window.sessionStorage.getItem('calligraphy-share:video_one'),null);
  d.getElementById('video-share-notice').close();state={active:true,...link};await open();state={active:false};
  d.getElementById('video-share-copy').click();await flush();assert.deepEqual(copied,[]);
  assert.equal(d.getElementById('video-share-url').value,'');
  d.getElementById('video-share-notice').close();state={active:true,...link};await open();state=null;
  d.getElementById('video-share-copy').click();await flush();assert.deepEqual(copied,[]);
  assert.equal(d.getElementById('video-share-create').disabled,true);
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
