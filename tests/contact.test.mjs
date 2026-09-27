import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import sharp from 'sharp';
import { createTextPlan } from '../src/text/plan.mjs';
import { describeContactStyle, renderContactStyle } from '../src/bridges/contact.mjs';

const python = process.env.CALLIGRAPHY_PYTHON || process.env.PYTHON || resolve('.venv/bin/python');
const available = spawnSync(python, ['-c', 'import calligraphy.contact_renderer']).status === 0;
const skip = available ? false : 'Install the Python engine to run contact integration checks';

test('contact bridge reports prepared coverage and renders a shared text plan', { skip }, async t => {
  const dir = await mkdtemp(join(tmpdir(), 'calligraphy-contact-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const { strokeCounts } = await describeContactStyle('lishu', { pythonPath: python });
  assert.equal(Object.keys(strokeCounts).length, 25);
  const plan = createTextPlan({ text: '人月人', strokeCounts, layout: { width: 240, height: 320 } });
  const output = join(dir, 'lishu.png');
  await renderContactStyle({ style: 'lishu', plan, output, pythonPath: python });
  const metadata = await sharp(output).metadata();
  assert.deepEqual([metadata.width, metadata.height], [240, 320]);
});

test('generic CLI routes prepared styles, rejects missing glyphs and never falls back', { skip }, async t => {
  const dir = await mkdtemp(join(tmpdir(), 'calligraphy-contact-cli-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const script = resolve('scripts/render-text.mjs');
  const run = args => spawnSync(process.execPath, [script, ...args], { cwd: dir, encoding: 'utf8', env: { ...process.env, CALLIGRAPHY_PYTHON: python } });
  for (const style of ['liu', 'yan-contact']) {
    const result = run(['--style', style, '--text', '人', '--width', '128', '--height', '128', '--output', join(dir, `${style}.png`)]);
    assert.equal(result.status, 0, result.stderr);
  }
  for (const [extra, expected] of [
    [['--text', '天地'], /Missing prepared lishu glyphs: 天 地/],
    [['--text', '人', '--fetch'], /template-only/],
    [['--text', '人', '--output', join(dir, 'bad.svg')], /not SVG/],
  ]) {
    const result = run(['--style', 'lishu', ...extra]);
    assert.equal(result.status, 1); assert.match(result.stderr, expected);
  }
});

test('contact bridge rejects an unavailable Python executable cleanly', async () => {
  await assert.rejects(describeContactStyle('lishu', { pythonPath: '/definitely/missing/python' }), /Cannot start contact renderer/);
});
