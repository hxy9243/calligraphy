import test from 'node:test';
import assert from 'node:assert/strict';
import { clamp, distance, tracePath, tracePolyline } from '../src/geometry.mjs';

test('clamp and distance cover shared scene geometry', () => {
  assert.equal(clamp(-2), 0);
  assert.equal(clamp(2), 1);
  assert.equal(clamp(4, 2, 5), 4);
  assert.equal(distance([0, 0], [3, 4]), 5);
});

test('tracePolyline follows cumulative segment length and reports its tip', () => {
  const traced = tracePolyline([[0, 0], [3, 0], [3, 4]], 0.5);
  assert.equal(traced.path, 'M 0.00 0.00 L 3.00 0.00 L 3.00 0.50');
  assert.deepEqual(traced.tip, [3, 0.5]);
  assert.equal(tracePath([[0, 0], [3, 0], [3, 4]], 1), 'M 0.00 0.00 L 3.00 0.00 L 3.00 4.00');
});

test('tracePolyline rejects missing geometry', () => {
  assert.throws(() => tracePolyline([], 0.5), /at least one point/);
});
