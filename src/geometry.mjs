export function clamp(value, low = 0, high = 1) {
  return Math.max(low, Math.min(high, value));
}

export function distance(a, b) {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

export function tracePolyline(points, fraction) {
  if (!Array.isArray(points) || points.length === 0) {
    throw new TypeError('tracePolyline requires at least one point');
  }

  const lengths = points.slice(1).map((point, index) => distance(points[index], point));
  let left = lengths.reduce((sum, length) => sum + length, 0) * clamp(fraction);
  const visited = [points[0]];

  for (let index = 0; index < lengths.length; index++) {
    if (left >= lengths[index]) {
      visited.push(points[index + 1]);
      left -= lengths[index];
    } else {
      const progress = lengths[index] ? left / lengths[index] : 0;
      visited.push([
        points[index][0] + (points[index + 1][0] - points[index][0]) * progress,
        points[index][1] + (points[index + 1][1] - points[index][1]) * progress,
      ]);
      break;
    }
  }

  const tip = visited[visited.length - 1];
  const path = `M ${visited.map(point => point.map(value => value.toFixed(2)).join(' ')).join(' L ')}`;
  return { path, tip, points: visited };
}

export function tracePath(points, fraction) {
  return tracePolyline(points, fraction).path;
}
