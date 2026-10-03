import { parseArgs } from 'node:util';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { resolveGlyphs, bundledGlyphs } from '../src/text/index.mjs';
import { parseText } from '../src/text/input.mjs';
import { describeContactStyle, prepareFontStyle } from '../src/bridges/contact.mjs';

async function main() {
  const strings = ['style', 'font', 'license', 'source', 'text', 'text-file', 'glyphs', 'workers'];
  const { values } = parseArgs({ options: {
    ...Object.fromEntries(strings.map(name => [name, { type: 'string' }])),
    fetch: { type: 'boolean' }, help: { type: 'boolean', short: 'h' },
  } });
  if (values.help) {
    console.log(`Prepare a local font for writing animation.
Usage: npm run prepare:font -- --style "lishu hanwang" --font FONT.ttf --license LICENSE.txt --text "春江花月夜" --fetch
New styles require --font and --license. --source records provenance.
Existing styles: omit --font/--license to prepare additional characters.
--glyphs FILE supplies local Hanzi Writer records; --fetch explicitly downloads missing records.
--text-file FILE is an alternative to --text. Rendering is offline after preparation.
--workers N sets parallel workers for fitting (default: 8).
CALLIGRAPHY_STYLE_DIR overrides ~/.local/share/calligraphy/styles.`);
    return;
  }
  if (!values.style) throw new Error('--style is required');
  if ((values.text !== undefined) === (values['text-file'] !== undefined)) throw new Error('Supply exactly one of --text or --text-file');
  const text = values.text ?? await readFile(values['text-file'], 'utf8');
  const { uniqueCharacters } = parseText(text);
  let needed = uniqueCharacters;
  if (!values.font) {
    const description = await describeContactStyle(values.style);
    if (!description.preparable) throw new Error('Choose a new font style name; built-in collections cannot be extended');
    needed = needed.filter(c => !Object.hasOwn(description.strokeCounts, c));
    if (!needed.length) { console.log(`All characters are already prepared for ${values.style}`); return; }
  } else if (!values.license) throw new Error('--license is required when supplying --font');
  const additional = values.glyphs ? JSON.parse(await readFile(values.glyphs, 'utf8')) : {};
  if (!additional || typeof additional !== 'object' || Array.isArray(additional)) throw new Error('--glyphs must be a dictionary');
  const glyphs = await resolveGlyphs(needed.join(''), { glyphs: { ...bundledGlyphs, ...additional }, fetchMissing: values.fetch ?? false });
  const workers = values.workers !== undefined ? Number(values.workers) : 8;
  const result = await prepareFontStyle({ style: values.style, glyphs,
    fontPath: values.font ? resolve(values.font) : undefined,
    licensePath: values.license ? resolve(values.license) : undefined, source: values.source, workers });
  const flagged = result.prepared.filter(c => result.metrics[c].review_required);
  console.log(`Registered ${result.style}: ${Object.keys(result.strokeCounts).length} prepared characters. Bank: ${result.path}`);
  if (flagged.length) console.log(`Review inferred stroke fits: ${flagged.join(' ')}`);
}
main().catch(error => { console.error(`Preparation failed: ${error.message}`); process.exitCode = 1; });
