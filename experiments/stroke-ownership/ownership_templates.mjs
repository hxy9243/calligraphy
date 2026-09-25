import fs from 'node:fs/promises';
import sharp from 'sharp';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(root,'ownership-characters.json'),'utf8'));
await fs.mkdir(path.join(root,'ownership-work/templates'),{recursive:true});
for(const [char,d] of Object.entries(data)) {
  const n=d.strokes.length;
  const body=d.strokes.map((path,i)=>`<g transform="translate(0 ${i*160}) scale(.15625) translate(0 900) scale(1 -1)"><path d="${path}" fill="white"/></g>`).join('');
  await sharp(Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="160" height="${n*160}"><rect width="100%" height="100%" fill="black"/>${body}</svg>`)).png().toFile(path.join(root,`ownership-work/templates/${char}.png`));
}
console.log('40 stroke templates rasterized');
