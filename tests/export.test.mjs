import test from 'node:test';
import assert from 'node:assert/strict';
import { access, mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import sharp from 'sharp';
import { finiteNumber, positiveInteger, positiveNumber } from '../src/export/config.mjs';
import { exportStill } from '../src/export/still.mjs';
import { encodeVideo } from '../src/export/video.mjs';

const smallFrame = time => `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="rgb(${Math.round(time * 10)},0,0)"/></svg>`;

async function rejectsQuickly(promise, pattern) {
  let timer;
  try {
    await assert.rejects(Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('encoder timed out')), 2000); }),
    ]), pattern);
  } finally {
    clearTimeout(timer);
  }
}

test('export configuration rejects unsafe dimensions and times', () => {
  assert.equal(positiveInteger('24', 'fps'), 24);
  assert.equal(positiveNumber('1.5', 'speed', { maximum: 10 }), 1.5);
  assert.equal(finiteNumber('0', 'time', { minimum: 0, maximum: 8 }), 0);
  assert.throws(() => positiveInteger(241, 'width', { even: true }), /even integer/);
  assert.throws(() => positiveNumber(11, 'speed', { maximum: 10 }), /\(0, 10\]/);
  assert.throws(() => finiteNumber(9, 'time', { minimum: 0, maximum: 8 }), /between 0 and 8/);
});

test('still exporter writes SVG and a dimensioned PNG from one frame function', async t => {
  const directory = await mkdtemp(join(tmpdir(), 'calligraphy-still-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const svgPath = join(directory, 'frame.svg');
  const pngPath = join(directory, 'frame.png');

  await exportStill({ frameSVG: smallFrame, time: 1, output: svgPath, width: 64, height: 48 });
  await exportStill({ frameSVG: smallFrame, time: 1, output: pngPath, width: 64, height: 48 });
  assert.match(await readFile(svgPath, 'utf8'), /rgb\(10,0,0\)/);
  assert.deepEqual(await sharp(pngPath).metadata().then(({ width, height }) => [width, height]), [64, 48]);
});

test('missing ffmpeg rejects promptly instead of hanging', async () => {
  await rejectsQuickly(encodeVideo({
    frameSVG: smallFrame, duration: 0.1, output: join(tmpdir(), 'unused.mp4'),
    fps: 1, width: 16, height: 16, ffmpegPath: '/definitely/missing/calligraphy-ffmpeg',
  }), /Could not start/);
});

test('an encoder that exits early rejects promptly without an unhandled stdin error', async () => {
  await rejectsQuickly(encodeVideo({
    frameSVG: smallFrame, duration: 0.1, output: join(tmpdir(), 'unused.mp4'),
    fps: 1, width: 16, height: 16, ffmpegPath: '/bin/false',
  }), /exited with 1/);
});

test('video encoder produces a playable smoke artifact when ffmpeg is available', { skip: spawnSync('ffmpeg', ['-version']).status !== 0 }, async t => {
  const directory = await mkdtemp(join(tmpdir(), 'calligraphy-video-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const output = join(directory, 'smoke.mp4');
  const result = await encodeVideo({ frameSVG: smallFrame, duration: 0.1, output, fps: 1, width: 16, height: 16 });
  await access(output);
  assert.equal(result.frameCount, 1);
  assert.ok((await stat(output)).size > 0);
});

test('video encoder validates output before launching a process', async () => {
  await assert.rejects(encodeVideo({ frameSVG: smallFrame, duration: 1, output: '', fps: 1, width: 16, height: 16 }), /output is required/);
});
