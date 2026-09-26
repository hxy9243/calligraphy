import { encodeVideo } from '../src/export/video.mjs';
import { positiveInteger, positiveNumber } from '../src/export/config.mjs';
import { getScene, sceneOptions } from '../src/scenes/index.mjs';

const scene = getScene('poem');
const fps = positiveInteger(process.env.FPS || 24, 'FPS');
const width = positiveInteger(process.env.WIDTH || 720, 'WIDTH', { minimum: 240, even: true });
const height = Math.round(width * 16 / 9);
const speed = positiveNumber(process.env.SPEED || 1, 'SPEED', { maximum: 10 });
const output = process.env.OUTPUT || 'poem-animation.mp4';
const options = sceneOptions({ style: process.env.STYLE, speed });

await encodeVideo({
  ...scene,
  fps,
  width,
  height,
  speed,
  output,
  options,
  crf: 19,
  ffmpegPath: process.env.FFMPEG || 'ffmpeg',
  onProgress({ index, elapsed, duration }) {
    if (index % fps === 0) process.stdout.write(`\rRendering ${elapsed} / ${duration.toFixed(1)} s`);
  },
});
console.log(`\nWrote ${output}`);
