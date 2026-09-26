import { encodeVideo } from '../src/export/video.mjs';
import { positiveInteger } from '../src/export/config.mjs';
import { getScene } from '../src/scenes/index.mjs';

const scene = getScene('yong');
const fps = positiveInteger(process.env.FPS || 24, 'FPS');
const size = positiveInteger(process.env.SIZE || 1080, 'SIZE', { minimum: 240, even: true });
const output = process.env.OUTPUT || 'yong-animation.mp4';

await encodeVideo({
  ...scene,
  fps,
  width: size,
  height: size,
  output,
  crf: 18,
  ffmpegPath: process.env.FFMPEG || 'ffmpeg',
  onProgress({ index, elapsed, duration }) {
    if (index % fps === 0) process.stdout.write(`\rRendering ${elapsed} / ${duration.toFixed(1)} s`);
  },
});
console.log(`\nWrote ${output}`);
