import sharp from 'sharp';
import { spawn } from 'node:child_process';
import { poemFrameSVG, DURATION } from '../src/poem-animation.mjs';
import styleMeasurements from '../experiments/style-transfer/diagnostics.json' with { type: 'json' };

const fps = Number(process.env.FPS || 24);
const width = Number(process.env.WIDTH || 720);
const output = process.env.OUTPUT || 'poem-animation.mp4';
const speed = Number(process.env.SPEED || 1);
const yan = process.env.STYLE === 'yan';
const options = { yan, speed, expansion: yan ? styleMeasurements.width_offset_px * 4 : 0 };
if (!Number.isFinite(speed) || speed <= 0 || speed > 10) throw new Error('SPEED must be in (0, 10]');
if (!Number.isInteger(fps) || fps < 1 || !Number.isInteger(width) || width < 240 || width % 2) {
  throw new Error('FPS must be positive; WIDTH must be an even integer >= 240');
}
const ffmpeg = spawn('ffmpeg', [
  '-y', '-loglevel', 'error', '-f', 'image2pipe', '-vcodec', 'png',
  '-framerate', String(fps), '-i', 'pipe:0', '-an', '-c:v', 'libx264',
  '-pix_fmt', 'yuv420p', '-crf', '19', '-movflags', '+faststart', output,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const exit = new Promise((resolve, reject) => {
  ffmpeg.on('error', reject);
  ffmpeg.on('close', code => code === 0 ? resolve() : reject(new Error(`ffmpeg exited ${code}`)));
});
try {
  for (let i = 0; i < Math.ceil(DURATION * fps / speed); i++) {
    const svg = poemFrameSVG(i / fps * speed, options);
    const png = await sharp(Buffer.from(svg)).resize(width, Math.round(width * 16 / 9)).png().toBuffer();
    if (!ffmpeg.stdin.write(png)) await new Promise(resolve => ffmpeg.stdin.once('drain', resolve));
    if (i % fps === 0) process.stdout.write(`\rRendering ${i / fps} / ${(DURATION / speed).toFixed(1)} s`);
  }
  ffmpeg.stdin.end();
  await exit;
  console.log(`\nWrote ${output}`);
} catch (error) {
  ffmpeg.stdin.destroy();
  throw error;
}
