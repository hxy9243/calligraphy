import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, extname } from 'node:path';
import sharp from 'sharp';
import { positiveInteger } from './config.mjs';

export async function exportStill({ frameSVG, time = 0, output, width, height, options = {} }) {
  if (typeof frameSVG !== 'function') throw new TypeError('frameSVG must be a function');
  if (!output) throw new TypeError('output is required');

  const svg = frameSVG(time, options);
  const extension = extname(output).toLowerCase();
  await mkdir(dirname(output), { recursive: true });

  if (extension === '.svg') {
    await writeFile(output, svg);
    return { output, format: 'svg', width, height };
  }
  if (extension !== '.png') throw new TypeError('Still output must end in .png or .svg');

  const targetWidth = positiveInteger(width, 'width');
  const targetHeight = positiveInteger(height, 'height');
  await sharp(Buffer.from(svg)).resize(targetWidth, targetHeight).png().toFile(output);
  return { output, format: 'png', width: targetWidth, height: targetHeight };
}
