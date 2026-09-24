import sharp from 'sharp';
import { spawn } from 'node:child_process';
import { frameSVG, DURATION } from '../src/animation.mjs';

const fps = Number(process.env.FPS || 24);
const size = Number(process.env.SIZE || 1080);
const output = process.env.OUTPUT || 'yong-animation.mp4';
if (!Number.isInteger(fps) || fps < 1 || !Number.isInteger(size) || size < 240) {
  throw new Error('FPS and SIZE must be positive integers (SIZE >= 240)');
}
const ffmpeg = spawn('ffmpeg', [
  '-y', '-loglevel', 'error', '-f', 'image2pipe', '-vcodec', 'png',
  '-framerate', String(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
  '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', output,
], { stdio: ['pipe', 'inherit', 'inherit'] });

const exit = new Promise((resolve, reject) => {
  ffmpeg.on('error', reject);
  ffmpeg.on('close', code => code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code}`)));
});

try {
  for (let i = 0; i < DURATION * fps; i++) {
    const svg = frameSVG(i / fps);
    const png = await sharp(Buffer.from(svg)).resize(size, size).png().toBuffer();
    if (!ffmpeg.stdin.write(png)) await new Promise(resolve => ffmpeg.stdin.once('drain', resolve));
    if (i % fps === 0) process.stdout.write(`\rRendering ${i / fps} / ${DURATION} s`);
  }
  ffmpeg.stdin.end();
  await exit;
  console.log(`\nWrote ${output}`);
} catch (error) {
  ffmpeg.stdin.destroy();
  throw error;
}
