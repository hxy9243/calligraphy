import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import sharp from 'sharp';
import { createTextScene, createTextPlan, resolveGlyphs, bundledGlyphs, parseText } from 'calligraphy-engine/text';

const glyph = () => ({ strokes: ['M 100 400 L 900 400 L 900 500 L 100 500 Z'], medians: [[[100, 450], [900, 450]]] });
const counts = { 明: 8, 月: 4, 永: 5, 清: 11 };

function assertInside(plan) {
  for (const p of plan.schedule) {
    assert.ok(p.x >= 0 && p.y >= 0);
    assert.ok(p.x + p.size <= plan.width + 1e-8);
    assert.ok(p.y + p.size <= plan.height + 1e-8);
  }
}

test('text preserves repeated glyphs and explicit lines, with a declared punctuation policy', () => {
  assert.deepEqual(parseText(' 明明，月\r\n永。').lines, [['明', '明'], ['月'], ['永']]);
  assert.deepEqual(parseText('明，月', { punctuation: 'omit' }).lines, [['明', '月']]);
  assert.deepEqual(parseText('明明月').uniqueCharacters, ['明', '月']);
  for (const text of ['', ' ，。 ', '明A', '明🙂', '永'.repeat(513)]) assert.throws(() => parseText(text));
  assert.throws(() => parseText('永', { punctuation: 'draw' }), /punctuation/);
});

test('plan wraps vertical text into distinct right-to-left columns and keeps input order', () => {
  const p = createTextPlan({ text: '明月永清明月', strokeCounts: counts, layout: { width: 600, height: 800, charactersPerLine: 2 } });
  assert.deepEqual(p.schedule.map(v => v.character), [...'明月永清明月']);
  assert.ok(p.schedule[0].x > p.schedule[2].x && p.schedule[2].x > p.schedule[4].x);
  assert.equal(p.schedule[0].x, p.schedule[1].x);
  assert.ok(p.schedule[0].y < p.schedule[1].y);
  assertInside(p);
});

test('horizontal text runs left-to-right, with explicit lines preserved even below wrap size', () => {
  const p = createTextPlan({ text: '明月\n永清', strokeCounts: counts, layout: { direction: 'horizontal-lr', charactersPerLine: 5 } });
  assert.ok(p.schedule[0].x < p.schedule[1].x);
  assert.equal(p.schedule[0].y, p.schedule[1].y);
  assert.ok(p.schedule[2].y > p.schedule[0].y);
  assertInside(p);
});

test('automatic layout fits short, repeated, narrow and wide text', () => {
  const explicit = createTextPlan({ text: '明月永清明\n明月永清明', strokeCounts: counts });
  assert.equal(explicit.schedule[4].line, 0);
  assert.equal(explicit.schedule[5].line, 1);
  for (const text of ['永', '明月永清'.repeat(10), '明\n月\n永\n清']) {
    for (const [width, height] of [[240, 720], [720, 240]]) {
      assertInside(createTextPlan({ text, strokeCounts: counts, layout: { width, height } }));
    }
  }
});

test('timing is based on actual stroke counts, including repeats, and has no trailing character gap', () => {
  const p = createTextPlan({ text: '明月明', strokeCounts: counts,
    timing: { intro: 1, outro: 2, characterGap: .5, strokeSeconds: .25 } });
  assert.deepEqual(p.schedule.map(({ start, end }) => [start, end]), [[1, 3], [3.5, 4.5], [5, 7]]);
  assert.equal(p.duration, 9);
  assert.deepEqual(JSON.parse(JSON.stringify(p)).schedule, p.schedule);
  assert.equal(p.schemaVersion, 1);
  assert.throws(() => { p.schedule[0].start = 0; }, TypeError);
});

test('invalid layout, timing and missing stroke counts fail before rendering', () => {
  for (const layout of [{ width: 0 }, { width: 10000 }, { height: NaN }, { margin: 800 }, { charactersPerLine: 0 }, { gap: -1 }, { direction: 'diagonal' }]) {
    assert.throws(() => createTextPlan({ text: '永', strokeCounts: counts, layout }));
  }
  for (const timing of [{ strokeSeconds: 0 }, { intro: -1 }, { outro: Infinity }, { characterGap: -1 }]) {
    assert.throws(() => createTextPlan({ text: '永', strokeCounts: counts, timing }));
  }
  assert.throws(() => createTextPlan({ text: '明月', strokeCounts: {} }), /明 月/);
  assert.throws(() => createTextPlan({ text: '永', strokeCounts: { 永: 0 } }), /stroke count/);
  assert.throws(() => createTextPlan({ text: '永'.repeat(100), strokeCounts: counts, layout: { width: 64, height: 64 } }), /too dense/);
});

test('scene reports all missing glyphs and rejects malformed data without fallback', () => {
  assert.throws(() => createTextScene({ text: '天地天', glyphs: {} }), /天 地/);
  for (const broken of [{ strokes: [], medians: [] }, { ...glyph(), medians: [[[NaN, 2], [3, 4]]] },
    { ...glyph(), strokes: ['M 0 0"/><script>alert(1)</script>'] }, { ...glyph(), medians: [] }]) {
    assert.throws(() => createTextScene({ text: '永', glyphs: { 永: broken } }), /Invalid glyph/);
  }
  assert.throws(() => createTextScene({ text: '永', style: 'lishu' }), /Unknown template style/);
});

test('scene snapshots input geometry and handles repeated glyph masks with unique ids', () => {
  const data = glyph();
  const scene = createTextScene({ text: '永永', glyphs: { 永: data } });
  const expected = scene.frameSVG(scene.duration);
  data.strokes[0] = 'M 0 0 Z';
  data.medians[0][0][0] = 999;
  assert.equal(scene.frameSVG(scene.duration), expected);
  assert.equal((expected.match(/data-character="永"/g) ?? []).length, 2);
  const a = scene.frameSVG(scene.schedule[0].start + .05);
  const b = scene.frameSVG(scene.schedule[1].start + .05);
  assert.match(a, /id="text-0-0"/);
  assert.match(b, /id="text-1-0"/);
  assert.equal(scene.frameSVG(-1), scene.frameSVG(0));
  assert.equal(scene.frameSVG(scene.duration + 10), expected);
  assert.throws(() => scene.frameSVG(NaN), /time/);
});

test('partial template frames accumulate ink and completion fills the outline even with zero outro', async () => {
  const scene = createTextScene({ text: '永', glyphs: { 永: glyph() }, layout: { width: 128, height: 128 },
    timing: { intro: 0, outro: 0, strokeSeconds: 1 } });
  let previous;
  for (const time of [0, .1, .3, .7, 1]) {
    const { data, info } = await sharp(Buffer.from(scene.frameSVG(time))).removeAlpha().raw().toBuffer({ resolveWithObject: true });
    const ink = Array.from({ length: info.width * info.height }, (_, i) => data[i * info.channels] < 150);
    if (previous) assert.ok(ink.every((value, i) => value || !previous[i]), `ink disappeared at ${time}`);
    else assert.ok(!ink.some(Boolean));
    previous = ink;
  }
  assert.ok(previous.some(Boolean));
  assert.doesNotMatch(scene.frameSVG(1), /<mask/);
});

test('template style changes widths without claiming a new glyph generator', () => {
  const a = createTextScene({ text: '永' });
  const b = createTextScene({ text: '永', style: 'yan' });
  assert.deepEqual(a.plan, b.plan);
  assert.match(b.frameSVG(b.duration), /stroke-width="16.48"/);
  assert.notEqual(a.frameSVG(a.duration), b.frameSVG(b.duration));
});

test('offline glyph resolution does not call fetch and distinguishes simplified/traditional', async () => {
  const glyphs = await resolveGlyphs('明明永', { fetchImpl: () => { throw new Error('unexpected network'); } });
  assert.deepEqual(Object.keys(glyphs), ['明', '永']);
  await assert.rejects(resolveGlyphs('間', { glyphs: bundledGlyphs }), /Missing glyphs: 間/);
});

test('explicit fetching is deduplicated, versioned and does not mutate supplied dictionaries', async () => {
  const input = { 永: glyph() }; const urls = [];
  const output = await resolveGlyphs('天地天永', { glyphs: input, fetchMissing: true,
    fetchImpl: async url => { urls.push(url); return { ok: true, json: async () => glyph() }; } });
  assert.equal(urls.length, 2);
  assert.ok(urls.every(url => url.includes('hanzi-writer-data@2.0.1/')));
  assert.deepEqual(Object.keys(input), ['永']);
  assert.deepEqual(Object.keys(output).sort(), ['永', '天', '地'].sort());
  await assert.rejects(resolveGlyphs('天', { glyphs: {}, fetchMissing: true,
    fetchImpl: async () => ({ ok: false, status: 404 }) }), /天: HTTP 404/);
  await assert.rejects(resolveGlyphs('天', { glyphs: {}, fetchMissing: true,
    fetchImpl: async () => ({ ok: true, json: async () => ({}) }) }), /Invalid glyph/);
});

test('generic command writes PNG/SVG from text files outside the repo and rejects missing glyphs', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'calligraphy-text-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const script = resolve('scripts/render-text.mjs');
  const input = join(dir, 'text.txt'); await writeFile(input, '永\n明月');
  for (const extension of ['png', 'svg']) {
    const output = join(dir, `page.${extension}`);
    const result = spawnSync(process.execPath, [script, '--text-file', input, '--output', output, '--width', '128', '--height', '192'], { cwd: dir, encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    if (extension === 'png') {
      const metadata = await sharp(output).metadata(); assert.deepEqual([metadata.width, metadata.height], [128, 192]);
    } else assert.match(await readFile(output, 'utf8'), /data-character="永"/);
  }
  const result = spawnSync(process.execPath, [script, '--text', '天地', '--output', join(dir, 'missing.png')], { cwd: dir, encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Missing glyphs: 天 地/);
});

test('generic command encodes an actual video when ffmpeg and ffprobe are available', {
  skip: ['ffmpeg', 'ffprobe'].some(command => spawnSync(command, ['-version']).status !== 0),
}, async t => {
  const dir = await mkdtemp(join(tmpdir(), 'calligraphy-text-video-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const output = join(dir, 'text.mp4');
  const result = spawnSync(process.execPath, ['scripts/render-text.mjs', '--text', '永', '--output', output,
    '--width', '128', '--height', '128', '--fps', '2', '--intro', '0', '--outro', '0', '--stroke-seconds', '.2'], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const probe = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'stream=width,height,nb_frames', '-of', 'json', output], { encoding: 'utf8' });
  assert.equal(probe.status, 0, probe.stderr);
  assert.deepEqual(JSON.parse(probe.stdout).streams[0], { width: 128, height: 128, nb_frames: '2' });
});
