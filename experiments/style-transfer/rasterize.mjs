// Render known ordered Hanzi Writer strokes; default target 永.
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';

const target=process.argv[2]||'永';
const files={'永':'../../data/yong.json'};
if(!files[target])throw Error(`No local stroke data for ${target}; add it to rasterize.mjs first`);
const here=path.dirname(new URL(import.meta.url).pathname);
const data=JSON.parse(fs.readFileSync(path.join(here,files[target]),'utf8'));
const out=path.join(here,'strokes-'+target);fs.mkdirSync(out,{recursive:true});
for(let i=0;i<data.strokes.length;i++){
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 1024 1024"><g transform="translate(0 900) scale(1 -1)"><path d="${data.strokes[i]}" fill="white"/></g></svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(out,`${String(i).padStart(2,'0')}.png`));
}
console.log(`Rasterized ${data.strokes.length} ordered strokes for ${target}`);
