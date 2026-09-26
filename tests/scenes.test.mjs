import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { getScene, sceneOptions, yanPreset } from '../src/scenes/index.mjs';
import { frameSVG } from '../src/scenes/yong.mjs';
import { DURATION as poemDuration, poemFrameSVG } from '../src/scenes/poem.mjs';
import * as packageApi from 'calligraphy-engine';
import * as yongApi from 'calligraphy-engine/scenes/yong';

const digest = value => createHash('sha256').update(value).digest('hex');

test('Yong frames exactly match the commit 94ccee4 deterministic baseline', () => {
  const baselines = new Map([
    [0, 'c2367b13ee9cb71f783eac4d9e5d0b5056f387a14104290376848c68fc467677'],
    [1.25, '2ee39ccd6c2a4869eb2fccd2d3c03196feb8cfd596ac74da29be4549c6b7e0a2'],
    [4, '9136ae3d525fb3beae6f0382466f1c4320358eacacc3d14bded600e723289361'],
    [8, '9dd649c375cf1a32f76db54226219155d961987729a24930f19b4e68fd452809'],
  ]);
  for (const [time, expected] of baselines) assert.equal(digest(frameSVG(time)), expected, `frame at ${time}s`);
});

test('poem frames exactly match the commit 94ccee4 deterministic baseline', () => {
  const baselines = new Map([
    [0, '71bbd40e5393d5f45f11d699a011413bfb0479d5d4d5d7ac8b9d4cae97902b82'],
    [1.5, '3d1607df28d864222ec8d207d7b48128af58ede3460623ea6f1582e93239c69a'],
    [10, '93504bd60575f1be3df1a2db459497cb385a407edb4432731468bdfab7e53882'],
    [poemDuration, 'd6648da01c8256a1216ea2d80c64aff97300959c8d52727e66b4f75624bbbfa3'],
  ]);
  for (const [time, expected] of baselines) assert.equal(digest(poemFrameSVG(time)), expected, `frame at ${time}s`);
});

test('promoted Yan preset preserves the prior styled frame', () => {
  const options = sceneOptions({ style: 'yan', speed: 1.5 });
  assert.equal(options.expansion, 16.48);
  assert.equal(digest(poemFrameSVG(10, options)), '8345fbf537d5336323e13c51ba8bf331d293e5b1990f948ce45486641260efc4');
  assert.equal(yanPreset.provenance.baseline_commit, '94ccee4');
});

test('scene registry validates names and exposes dimensions', () => {
  assert.deepEqual([getScene('yong').width, getScene('yong').height], [1080, 1080]);
  assert.deepEqual([getScene('poem').width, getScene('poem').height], [1080, 1920]);
  assert.throws(() => getScene('unknown'), /Unknown scene/);
  assert.throws(() => sceneOptions({ style: 'unknown' }), /Unknown style/);
});

test('package exports expose the public scene and helper API', () => {
  assert.equal(packageApi.getScene('yong').frameSVG, frameSVG);
  assert.equal(packageApi.tracePath([[0, 0], [1, 1]], 1), 'M 0.00 0.00 L 1.00 1.00');
  assert.equal(yongApi.frameSVG, frameSVG);
});
