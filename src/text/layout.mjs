import { finiteNumber, positiveInteger } from '../export/config.mjs';

function pseudoRand(i, j = 0) {
  let n = ((i * 374761393 + j * 668265263 + 1013904223) >>> 0);
  n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
  n = (n ^ (n >>> 16)) >>> 0;
  return (n / 2147483647.5) - 1.0;
}

/** One fitted page; explicit lines remain separate and long lines wrap. */
export function layoutText(lines, { width = 1080, height = 1440, direction = 'vertical-rl',
  charactersPerLine, margin = Math.min(width, height) * 0.07, gap = 0.18, zigzag = false } = {}) {
  width = positiveInteger(width, 'width', { minimum: 64 });
  height = positiveInteger(height, 'height', { minimum: 64 });
  if (width > 8192 || height > 8192) throw new RangeError('Page dimensions must not exceed 8192');
  if (!['vertical-rl', 'horizontal-lr'].includes(direction)) throw new TypeError('direction must be vertical-rl or horizontal-lr');
  margin = finiteNumber(margin, 'margin', { minimum: 0 });
  gap = finiteNumber(gap, 'gap', { minimum: 0, maximum: 2 });
  if (typeof zigzag !== 'boolean') throw new TypeError('zigzag must be a boolean');
  const availableWidth = width - margin * 2, availableHeight = height - margin * 2;
  if (availableWidth <= 0 || availableHeight <= 0) throw new RangeError('Margins leave no space for writing');
  const vertical = direction === 'vertical-rl';
  const count = lines.flat().length;
  const perLine = charactersPerLine === undefined
    ? (lines.length > 1 ? Math.max(...lines.map(line => line.length))
      : Math.max(1, Math.ceil(Math.sqrt(count * (vertical ? availableHeight / availableWidth : availableWidth / availableHeight)))))
    : positiveInteger(charactersPerLine, 'charactersPerLine');
  const wrapped = lines.flatMap(line => Array.from({ length: Math.ceil(line.length / perLine) },
    (_, index) => line.slice(index * perLine, (index + 1) * perLine)));
  const longest = Math.max(...wrapped.map(line => line.length));
  const columns = vertical ? wrapped.length : longest, rows = vertical ? longest : wrapped.length;
  const baseColDenom = columns + (columns - 1) * gap, baseRowDenom = rows + (rows - 1) * gap;
  const zigzagPad = (zigzag && count > 1) ? 0.52 : 0;
  const colDenom = baseColDenom + (vertical ? 0 : zigzagPad);
  const rowDenom = baseRowDenom + (vertical ? zigzagPad : 0);
  const cell = Math.min(availableWidth / colDenom, availableHeight / rowDenom);
  if (cell < 16) throw new RangeError('Text is too dense for this page; use a larger page or fewer characters');
  const left = (width - cell * baseColDenom) / 2;
  const top = (height - cell * baseRowDenom) / 2;
  const slackAlong = Math.max(0, vertical ? (availableHeight - cell * baseRowDenom) : (availableWidth - cell * baseColDenom));
  const ampAlong = (zigzag && count > 1) ? Math.min(cell * 0.35, slackAlong * 0.52) : 0;
  let normLineOffsets = [];
  if (zigzag && wrapped.length > 1) {
    const rawOffsets = wrapped.map((_, idx) => pseudoRand(idx + 1));
    const mean = rawOffsets.reduce((acc, v) => acc + v, 0) / rawOffsets.length;
    const centered = rawOffsets.map(v => v - mean);
    const maxAbs = Math.max(...centered.map(Math.abs)) || 1.0;
    normLineOffsets = centered.map(v => v / maxAbs);
  } else {
    normLineOffsets = new Array(Math.max(1, wrapped.length)).fill(0);
  }
  const placements = wrapped.flatMap((line, lineIndex) => line.map((character, index) => {
    const column = vertical ? columns - 1 - lineIndex : index;
    const row = vertical ? index : lineIndex;
    let x = left + column * cell * (1 + gap), y = top + row * cell * (1 + gap);
    if (ampAlong > 0) {
      const lineStagger = normLineOffsets[lineIndex] * ampAlong;
      const charJitter = pseudoRand(lineIndex + 1, index + 1) * (cell * 0.09);
      const shiftAlong = lineStagger + charJitter;
      const shiftAcross = pseudoRand(lineIndex + 101, index + 1) * Math.min(cell * 0.05, cell * gap * 0.32);
      if (vertical) {
        y = Math.max(margin, Math.min(height - margin - cell, y + shiftAlong));
        x = Math.max(margin, Math.min(width - margin - cell, x + shiftAcross));
      } else {
        x = Math.max(margin, Math.min(width - margin - cell, x + shiftAlong));
        y = Math.max(margin, Math.min(height - margin - cell, y + shiftAcross));
      }
    }
    return { character, line: lineIndex, column, row, x, y, size: cell };
  }));
  return { width, height, direction, charactersPerLine: perLine, columns, rows, zigzag, placements };
}
