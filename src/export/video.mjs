import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import sharp from 'sharp';
import { positiveInteger, positiveNumber } from './config.mjs';

function waitForSpawn(child, executable) {
  return new Promise((resolve, reject) => {
    child.once('spawn', resolve);
    child.once('error', error => reject(new Error(`Could not start ${executable}: ${error.message}`, { cause: error })));
  });
}

function waitForExit(child, executable) {
  return new Promise((resolve, reject) => {
    child.once('error', error => reject(new Error(`${executable} failed: ${error.message}`, { cause: error })));
    child.once('close', (code, signal) => {
      if (code === 0) resolve();
      else reject(new Error(`${executable} exited with ${code ?? `signal ${signal}`}`));
    });
  });
}

function writeFrame(stream, buffer) {
  return new Promise((resolve, reject) => {
    stream.write(buffer, error => error ? reject(error) : resolve());
  });
}

export async function encodeVideo({
  frameSVG,
  duration,
  output,
  fps = 24,
  width,
  height,
  speed = 1,
  crf = 19,
  options = {},
  ffmpegPath = 'ffmpeg',
  onProgress,
}) {
  if (typeof frameSVG !== 'function') throw new TypeError('frameSVG must be a function');
  if (!output) throw new TypeError('output is required');
  const frameRate = positiveInteger(fps, 'fps');
  const targetWidth = positiveInteger(width, 'width', { minimum: 2, even: true });
  const targetHeight = positiveInteger(height, 'height', { minimum: 2, even: true });
  const playbackSpeed = positiveNumber(speed, 'speed', { maximum: 10 });
  const sceneDuration = positiveNumber(duration, 'duration');
  const frameCount = Math.ceil(sceneDuration * frameRate / playbackSpeed);

  await mkdir(dirname(output), { recursive: true });
  const child = spawn(ffmpegPath, [
    '-y', '-loglevel', 'error', '-f', 'image2pipe', '-vcodec', 'png',
    '-framerate', String(frameRate), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p', '-crf', String(crf), '-movflags', '+faststart', output,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  let exitError;
  const exited = waitForExit(child, ffmpegPath).catch(error => {
    exitError = error;
  });
  let streamError;
  child.stdin.on('error', error => {
    streamError = error;
  });

  let started = false;
  try {
    await waitForSpawn(child, ffmpegPath);
    started = true;
    for (let index = 0; index < frameCount; index++) {
      const sceneTime = index / frameRate * playbackSpeed;
      const svg = frameSVG(sceneTime, options);
      const png = await sharp(Buffer.from(svg)).resize(targetWidth, targetHeight).png().toBuffer();
      await writeFrame(child.stdin, png);
      onProgress?.({ index, frameCount, elapsed: index / frameRate, duration: sceneDuration / playbackSpeed });
    }
    child.stdin.end();
    await exited;
    if (exitError) throw exitError;
    if (streamError) throw streamError;
  } catch (error) {
    child.stdin.destroy();
    if (child.exitCode === null && child.signalCode === null) child.kill();
    await exited;
    throw started ? (exitError || streamError || error) : error;
  }

  return { output, frameCount, fps: frameRate, width: targetWidth, height: targetHeight };
}
