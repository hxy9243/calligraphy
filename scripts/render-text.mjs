import { parseArgs } from 'node:util';
import { readFile } from 'node:fs/promises';
import { extname } from 'node:path';
import { createTextScene, createTextPlan, resolveGlyphs, bundledGlyphs } from '../src/text/index.mjs';
import { CONTACT_STYLES, describeContactStyle, renderContactStyle } from '../src/bridges/contact.mjs';
import { exportStill } from '../src/export/still.mjs';
import { encodeVideo } from '../src/export/video.mjs';
import { finiteNumber, positiveInteger, positiveNumber } from '../src/export/config.mjs';

const HELP = `Render text with template strokes or prepared contact-brush glyphs.
Usage: npm run render:text -- --text "明月松间照，清泉石上流" --output outputs/text.png

Input:   --text TEXT | --text-file FILE   (exactly one required)
         --glyphs FILE                  additional glyph dictionary JSON
         --fetch                        explicitly fetch missing Hanzi Writer records
Output:  --output FILE                   .svg, .png, or .mp4 (default outputs/text.png)
         --width N --height N            native page size (default 1080 x 1440)
Layout:  --direction vertical-rl|horizontal-lr (default vertical-rl)
         --per-line N                   wrap after N characters; otherwise automatic
         --punctuation break|omit        punctuation is not drawn (default break)
Style:   --style kai|yan|lishu|liu|yan-contact
         kai/yan use templates; the others use prepared contact glyphs (PNG/MP4).
Timing:  --stroke-seconds N --gap N      default .18 seconds/stroke, .15 between glyphs
         --intro N --outro N             default .5 and 1 seconds
Still:   --time N                       scene time; defaults to completed writing
Video:   --fps N --speed N               default 24 fps, speed 1 (maximum 10)
         FFMPEG selects the encoder; CALLIGRAPHY_PYTHON selects a Python installation
         with calligraphy-engine installed for contact styles.
`;

async function main() {
  const stringFlags = ['text', 'text-file', 'glyphs', 'output', 'width', 'height', 'direction', 'per-line',
    'punctuation', 'style', 'stroke-seconds', 'gap', 'intro', 'outro', 'time', 'fps', 'speed'];
  const { values } = parseArgs({ options: {
    ...Object.fromEntries(stringFlags.map(flag => [flag, { type: 'string' }])),
    fetch: { type: 'boolean' }, help: { type: 'boolean', short: 'h' },
  }, allowPositionals: false });
  if (values.help) { console.log(HELP); return; }
  if ((values.text !== undefined) === (values['text-file'] !== undefined)) throw new Error('Supply exactly one of --text or --text-file');
  const text = values.text ?? await readFile(values['text-file'], 'utf8');
  const output = values.output ?? 'outputs/text.png';
  const format = extname(output).toLowerCase();
  if (!['.png', '.svg', '.mp4'].includes(format)) throw new Error('Output must end in .png, .svg or .mp4');
  if (format === '.mp4' && values.time !== undefined) throw new Error('--time applies only to still images');
  if (format !== '.mp4' && (values.fps !== undefined || values.speed !== undefined)) throw new Error('--fps and --speed apply only to video');
  const style = values.style ?? 'kai';
  if (!['kai', 'yan', ...CONTACT_STYLES].includes(style)) throw new Error(`Unknown style: ${style}`);
  const layout = { width: values.width ?? 1080, height: values.height ?? 1440,
    direction: values.direction ?? 'vertical-rl', charactersPerLine: values['per-line'] };
  const timing = { strokeSeconds: values['stroke-seconds'], characterGap: values.gap, intro: values.intro, outro: values.outro };
  const punctuation = values.punctuation ?? 'break';
  if (CONTACT_STYLES.includes(style)) {
    if (format === '.svg') throw new Error('Contact brush styles export PNG or MP4, not SVG');
    if (values.fetch || values.glyphs) throw new Error('Contact styles use their prepared glyph collection; --fetch and --glyphs are template-only');
    const { strokeCounts } = await describeContactStyle(style);
    const missing = [...new Set([...text].filter(c => /\p{Script=Han}/u.test(c) && !Object.hasOwn(strokeCounts, c)))];
    if (missing.length) throw new Error(`Missing prepared ${style} glyphs: ${missing.join(' ')}. No template fallback is applied.`);
    const plan = createTextPlan({ text, strokeCounts, layout, timing, punctuation });
    if (plan.omitted.length) console.log(`Layout separators (not painted): ${JSON.stringify(plan.omitted)}`);
    const time = values.time === undefined ? undefined : finiteNumber(values.time, 'time', { minimum: 0, maximum: plan.duration });
    const fps = positiveInteger(values.fps ?? 24, 'fps');
    const speed = positiveNumber(values.speed ?? 1, 'speed', { maximum: 10 });
    await renderContactStyle({ style, plan, output, time, fps, speed });
    console.log(`Wrote ${output}: ${style} contact brush, ${plan.schedule.length} characters, ${plan.width}x${plan.height}`);
    return;
  }
  const additional = values.glyphs ? JSON.parse(await readFile(values.glyphs, 'utf8')) : {};
  if (!additional || typeof additional !== 'object' || Array.isArray(additional)) throw new Error('--glyphs must contain a character-keyed object');
  const glyphs = await resolveGlyphs(text, { glyphs: { ...bundledGlyphs, ...additional },
    fetchMissing: values.fetch ?? false, punctuation });
  const scene = createTextScene({ text, glyphs, style, punctuation, layout, timing });
  if (scene.omitted.length) console.log(`Layout separators (not painted): ${JSON.stringify(scene.omitted)}`);
  if (format === '.mp4') {
    const fps = positiveInteger(values.fps ?? 24, 'fps');
    const speed = positiveNumber(values.speed ?? 1, 'speed', { maximum: 10 });
    await encodeVideo({ ...scene, output, fps, speed, ffmpegPath: process.env.FFMPEG ?? 'ffmpeg' });
  } else {
    const time = finiteNumber(values.time ?? scene.duration, 'time', { minimum: 0, maximum: scene.duration });
    await exportStill({ ...scene, output, time });
  }
  console.log(`Wrote ${output}: ${scene.schedule.length} characters, ${scene.width}x${scene.height}, scene ${scene.duration.toFixed(2)}s`);
}
main().catch(error => { console.error(`Render failed: ${error.message}`); process.exitCode = 1; });
