import { resolve } from 'node:path';
import { exportStill } from '../src/export/still.mjs';
import { finiteNumber, positiveInteger, positiveNumber } from '../src/export/config.mjs';
import { getScene, sceneOptions } from '../src/scenes/index.mjs';

const scene = getScene(process.env.SCENE || 'yong');
const time = finiteNumber(process.env.TIME ?? scene.duration, 'TIME', { minimum: 0, maximum: scene.duration });
const speed = positiveNumber(process.env.SPEED || 1, 'SPEED', { maximum: 10 });
const width = positiveInteger(process.env.WIDTH || process.env.SIZE || scene.width, 'WIDTH');
const height = positiveInteger(process.env.HEIGHT || Math.round(scene.height / scene.width * width), 'HEIGHT');
const output = resolve(process.env.OUTPUT || `outputs/${scene.name}.png`);
const options = sceneOptions({ style: process.env.STYLE, speed });

const result = await exportStill({ ...scene, time, output, width, height, options });
console.log(`Wrote ${result.format.toUpperCase()} ${result.width}x${result.height} to ${result.output}`);
