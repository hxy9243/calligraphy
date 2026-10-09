import test from 'node:test';
import assert from 'node:assert/strict';
import { createFrontend, flush, jsonResponse } from './helpers/frontend.mjs';

const jobs = [
  { job_id: 'prev_old', text: '永', style: 'kai', created_at: '2026-10-04T00:00:00', job_type: 'preview', status: 'succeeded', download_url: '/fixtures/history.svg' },
  { job_id: 'vid_old', text: '永', style: 'kai', created_at: '2026-10-04T00:01:00', job_type: 'render', status: 'succeeded', video_url: '/fixtures/history.mp4', download_url: '/fixtures/download.mp4' },
];

const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100"/></svg>';
const hidden = element => element.classList.contains('hidden');

test('SVG, direct image, video, and history previews keep the image mounted across repeated transitions', async t => {
  let previewResponse = { svg };
  const ui = await createFrontend({ jobs, fetch: ({ url }) => {
    if (url === '/api/previews') return jsonResponse(previewResponse);
  } });
  t.after(ui.close);
  const { document, mediaEvents } = ui;
  const img = document.getElementById('preview-img');
  const imageContainer = document.getElementById('preview-image-container');
  const svgContainer = document.getElementById('preview-svg-container');
  const videoContainer = document.getElementById('video-container');
  const exportBox = document.getElementById('export-output-box');
  const video = document.getElementById('result-video');
  const historyView = [...document.querySelectorAll('#jobs-list button')].find(button => button.textContent.includes('查看'));
  const historyPlay = [...document.querySelectorAll('#jobs-list button')].find(button => button.textContent.includes('播放'));
  const preview = async response => {
    previewResponse = response;
    document.getElementById('btn-preview').click();
    await flush();
  };
  const assertImage = url => {
    assert.equal(document.getElementById('preview-img'), img);
    assert.equal(img.parentNode, imageContainer);
    assert.equal(img.getAttribute('src'), url);
    assert.equal(hidden(img), false);
    assert.equal(hidden(imageContainer), false);
    assert.equal(hidden(exportBox), false);
    assert.equal(hidden(videoContainer), true);
    assert.equal(svgContainer.querySelectorAll('svg').length, 0);
    assert.equal(hidden(svgContainer), true);
  };

  for (let pass = 0; pass < 2; pass++) {
    await preview({ svg });
    assert.equal(img.parentNode, imageContainer);
    assert.equal(hidden(img), true);
    assert.equal(hidden(svgContainer), false);
    assert.equal(imageContainer.querySelectorAll('svg').length, 1);
    assert.equal(hidden(imageContainer), false);
    historyView.click();
    assert.equal(document.querySelector('#detail-viewer img').getAttribute('src'), '/fixtures/history.svg');
    document.getElementById('job-detail').close();

    await preview({ svg });
    await preview({ svg });
    assert.equal(imageContainer.querySelectorAll('svg').length, 1);
    historyPlay.click();
    assert.equal(document.getElementById('job-detail').open, true);
    assert.equal(document.querySelector('#detail-viewer video').getAttribute('src'), '/fixtures/history.mp4');
    assert.equal(document.getElementById('detail-download').getAttribute('href'), '/fixtures/download.mp4');
    document.getElementById('job-detail').close();
    assert.equal(document.querySelector('#detail-viewer video'), null);
    assert.equal(mediaEvents.some(e => e.method === 'pause'), true);

    historyPlay.click();
    await preview({ svg });
    assert.equal(hidden(videoContainer), true);
    assert.equal(mediaEvents.at(-1).method, 'pause');
    await preview({ preview_url: '/fixtures/direct.png' });
    assertImage('/fixtures/direct.png');

    historyPlay.click();
    await preview({ preview_url: '/fixtures/another.png' });
    assertImage('/fixtures/another.png');
    assert.equal(mediaEvents.at(-1).method, 'pause');
  }
});
