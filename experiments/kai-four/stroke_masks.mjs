// Rasterize Hanzi Writer's ordered vector outlines separately for mask registration.
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

const here = path.dirname(new URL(import.meta.url).pathname);
const { strokes } = JSON.parse(fs.readFileSync(path.join(here, 'shu.json'), 'utf8'));
const out = path.join(here, 'stroke-masks');
fs.mkdirSync(out, { recursive: true });
for (let i = 0; i < strokes.length; i++) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 1024 1024"><g transform="translate(0 900) scale(1 -1)"><path fill="white" d="${strokes[i]}"/></g></svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(out, `${i.toString().padStart(2, '0')}.png`));
}
console.log(`Wrote ${strokes.length} individual masks`);
