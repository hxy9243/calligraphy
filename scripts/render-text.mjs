import { parseArgs } from 'node:util';
import { readFile } from 'node:fs/promises';
import { extname } from 'node:path';
import { createTextScene, createTextPlan, resolveGlyphs, bundledGlyphs } from '../src/text/index.mjs';
import { CONTACT_STYLES, describeContactStyle, renderContactStyle, prepareFontStyle, listContactStyles, renderKaiScene } from '../src/bridges/contact.mjs';
import { exportStill } from '../src/export/still.mjs';
import { encodeVideo } from '../src/export/video.mjs';
import { finiteNumber, positiveInteger, positiveNumber } from '../src/export/config.mjs';

const HELP = `Render text with fitted Kai Stroke IR or prepared style glyphs.
Usage: npm run render:text -- --text "明月松间照，清泉石上流" --output outputs/text.png

Engine:  --mode auto|stroke_ir|template   generic Kai defaults to stroke_ir
Styles:  --list-styles                  list built-in and locally registered styles
Input:   --text TEXT | --text-file FILE   (exactly one required)
         --glyphs FILE                  additional glyph dictionary JSON
         --fetch                        explicitly fetch missing Hanzi Writer records
Output:  --output FILE                   .svg, .png, or .mp4 (default outputs/text.png)
         --width N --height N            native page size (default 1080 x 1440)
Layout:  --direction vertical-rl|horizontal-lr (default vertical-rl)
         --per-line N                   wrap after N characters; otherwise automatic
         --punctuation break|omit        punctuation is not drawn (default break)
Style:   --style kai|yan|lishu|liu|yan-contact|"lishu hanwang"
         Registered font styles prepare missing characters with --fetch or --glyphs.
         kai uses fitted Stroke IR; yan uses templates; the others use prepared contact glyphs (PNG/MP4).
Timing:  --stroke-seconds N --gap N      default .18 seconds/stroke, .15 between glyphs
         --intro N --outro N             default .5 and 1 seconds
Still:   --time N                       scene time; defaults to completed writing
Video:   --fps N --speed N               default 24 fps, speed 1 (maximum 10)
         --workers N                     parallel workers (default: 8)
         FFMPEG selects the encoder; CALLIGRAPHY_PYTHON selects a Python installation
         with calligraphy-engine installed for contact styles.
`;

async function main() {
  const stringFlags = ['text', 'text-file', 'glyphs', 'output', 'width', 'height', 'direction', 'per-line',
    'punctuation', 'style', 'stroke-seconds', 'gap', 'intro', 'outro', 'time', 'fps', 'speed', 'workers', 'mode'];
  const { values } = parseArgs({ options: {
    ...Object.fromEntries(stringFlags.map(flag => [flag, { type: 'string' }])),
    'list-styles': { type: 'boolean' }, fetch: { type: 'boolean' }, help: { type: 'boolean', short: 'h' },
  }, allowPositionals: false });
  if (values.help) { console.log(HELP); return; }
  if (values['list-styles']) {
    console.log('kai: fitted Stroke IR (default)\nyan: template width preset');
    for (const entry of await listContactStyles()) console.log(`${entry.style}: ${entry.prepared} prepared glyphs${entry.preparable ? ', extensible font' : ''}`);
    return;
  }
  if ((values.text !== undefined) === (values['text-file'] !== undefined)) throw new Error('Supply exactly one of --text or --text-file');
  const text = values.text ?? await readFile(values['text-file'], 'utf8');
  const output = values.output ?? 'outputs/text.png';
  const format = extname(output).toLowerCase();
  if (!['.png', '.svg', '.mp4'].includes(format)) throw new Error('Output must end in .png, .svg or .mp4');
  if (format === '.mp4' && values.time !== undefined) throw new Error('--time applies only to still images');
  if (format !== '.mp4' && (values.fps !== undefined || values.speed !== undefined)) throw new Error('--fps and --speed apply only to video');
  const workers = values.workers !== undefined ? positiveInteger(values.workers, 'workers') : 8;
  const style = values.style ?? 'kai';
  const mode = values.mode ?? 'auto';
  if (!['auto', 'template', 'stroke_ir'].includes(mode)) throw new Error('Mode must be auto, template or stroke_ir');
  if (mode === 'stroke_ir' && style !== 'kai') throw new Error('stroke_ir mode supports generic kai only');
  if (mode === 'template' && !['kai', 'yan'].includes(style)) throw new Error('template mode supports kai and yan only');
  const layout = { width: values.width ?? 1080, height: values.height ?? 1440,
    direction: values.direction ?? 'vertical-rl', charactersPerLine: values['per-line'] };
  const timing = { strokeSeconds: values['stroke-seconds'], characterGap: values.gap, intro: values.intro, outro: values.outro };
  const punctuation = values.punctuation ?? 'break';
  if (!['kai', 'yan'].includes(style)) {
    if (format === '.svg') throw new Error('Contact brush styles export PNG or MP4, not SVG');
    if (CONTACT_STYLES.includes(style) && (values.fetch || values.glyphs)) throw new Error('Prepared contact collections cannot be extended; --fetch and --glyphs are template-only for these built-in styles');
    let { strokeCounts, preparable, source } = await describeContactStyle(style);
    const missing = [...new Set([...text].filter(c => /\p{Script=Han}/u.test(c) && !Object.hasOwn(strokeCounts, c)))];
    if (missing.length && preparable && (values.fetch || values.glyphs)) {
      // Validate text/layout/timing before fitting. Temporary counts are validation only.
      createTextPlan({ text, strokeCounts: { ...strokeCounts, ...Object.fromEntries(missing.map(c => [c, 1])) }, layout, timing, punctuation });
      const additional = values.glyphs ? JSON.parse(await readFile(values.glyphs, 'utf8')) : {};
      if (!additional || typeof additional !== 'object' || Array.isArray(additional)) throw new Error('--glyphs must be a dictionary');
      const glyphs = await resolveGlyphs(missing.join(''), { glyphs: { ...bundledGlyphs, ...additional }, fetchMissing: values.fetch ?? false });
      const prepared = await prepareFontStyle({ style, glyphs, workers });
      strokeCounts = prepared.strokeCounts;
      source = { metrics: prepared.metrics };
    } else if (missing.length) throw new Error(`Missing prepared ${style} glyphs: ${missing.join(' ')}. ${preparable ? 'Use --fetch or --glyphs to prepare them from the registered font.' : 'No template fallback is applied.'}`);
    const review = [...new Set([...text])].filter(c => source?.metrics?.[c]?.review_required);
    if (review.length) console.warn(`Review inferred stroke fits for ${style}: ${review.join(' ')}`);
    const plan = createTextPlan({ text, strokeCounts, layout, timing, punctuation });
    if (plan.omitted.length) console.log(`Layout separators (not painted): ${JSON.stringify(plan.omitted)}`);
    const time = values.time === undefined ? undefined : finiteNumber(values.time, 'time', { minimum: 0, maximum: plan.duration });
    const fps = positiveInteger(values.fps ?? 24, 'fps');
    const speed = positiveNumber(values.speed ?? 1, 'speed', { maximum: 10 });
    await renderContactStyle({ style, plan, output, time, fps, speed, workers });
    console.log(`Wrote ${output}: ${style} contact brush, ${plan.schedule.length} characters, ${plan.width}x${plan.height}`);
    return;
  }
  const additional = values.glyphs ? JSON.parse(await readFile(values.glyphs, 'utf8')) : {};
  if (!additional || typeof additional !== 'object' || Array.isArray(additional)) throw new Error('--glyphs must contain a character-keyed object');
  const glyphs = await resolveGlyphs(text, { glyphs: { ...bundledGlyphs, ...additional },
    fetchMissing: values.fetch ?? false, punctuation });
  if (style === 'kai' && mode !== 'template') {
    const strokeCounts = Object.fromEntries(Object.entries(glyphs).map(([c, g]) => [c, g.strokes.length]));
    const plan = createTextPlan({ text, strokeCounts, punctuation, layout, timing });
    const time = values.time === undefined ? undefined : finiteNumber(values.time, 'time', { minimum: 0, maximum: plan.duration });
    const fps = positiveInteger(values.fps ?? 24, 'fps');
    const speed = positiveNumber(values.speed ?? 1, 'speed', { maximum: 10 });
    await renderKaiScene({ glyphs, plan, output, time, fps, speed, workers, ffmpeg: process.env.FFMPEG ?? 'ffmpeg' });
    if (plan.omitted.length) console.log(`Layout separators (not painted): ${JSON.stringify(plan.omitted)}`);
    console.log(`Wrote ${output}: kai-fitted, ${plan.schedule.length} characters, ${plan.width}x${plan.height}`);
    return;
  }
  const scene = createTextScene({ text, glyphs, style, punctuation, layout, timing });
  if (scene.omitted.length) console.log(`Layout separators (not painted): ${JSON.stringify(scene.omitted)}`);
  if (format === '.mp4') {
    const fps = positiveInteger(values.fps ?? 24, 'fps');
    const speed = positiveNumber(values.speed ?? 1, 'speed', { maximum: 10 });
    await encodeVideo({ ...scene, output, fps, speed, ffmpegPath: process.env.FFMPEG ?? 'ffmpeg', workers });
  } else {
    const time = finiteNumber(values.time ?? scene.duration, 'time', { minimum: 0, maximum: scene.duration });
    await exportStill({ ...scene, output, time });
  }
  console.log(`Wrote ${output}: ${scene.schedule.length} characters, ${scene.width}x${scene.height}, scene ${scene.duration.toFixed(2)}s`);
}
main().catch(error => { console.error(`Render failed: ${error.message}`); process.exitCode = 1; });
