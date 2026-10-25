import { finiteNumber, positiveInteger } from '../export/config.mjs';

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
  const zigzagPad = (zigzag && count > 1) ? 0.44 : 0;
  const colDenom = baseColDenom + (vertical ? 0 : zigzagPad);
  const rowDenom = baseRowDenom + (vertical ? zigzagPad : 0);
  const cell = Math.min(availableWidth / colDenom, availableHeight / rowDenom);
  if (cell < 16) throw new RangeError('Text is too dense for this page; use a larger page or fewer characters');
  const left = (width - cell * baseColDenom) / 2;
  const top = (height - cell * baseRowDenom) / 2;
  const slackAlong = Math.max(0, vertical ? (availableHeight - cell * baseRowDenom) : (availableWidth - cell * baseColDenom));
  const ampAlong = (zigzag && count > 1) ? Math.min(cell * 0.24, slackAlong * 0.46) : 0;
  const placements = wrapped.flatMap((line, lineIndex) => line.map((character, index) => {
    const column = vertical ? columns - 1 - lineIndex : index;
    const row = vertical ? index : lineIndex;
    let x = left + column * cell * (1 + gap), y = top + row * cell * (1 + gap);
    if (ampAlong > 0) {
      const sign = (lineIndex % 2 === 1) ? -1 : 1;
      const lineWave = sign * (0.72 + 0.28 * Math.sin(lineIndex * 1.7 + 0.4));
      const charWave = 0.28 * Math.sin(index * 1.45 + lineIndex * 1.1);
      const shiftAlong = ampAlong * Math.max(-1, Math.min(1, lineWave + charWave));
      if (vertical) y = Math.max(margin, Math.min(height - margin - cell, y + shiftAlong));
      else x = Math.max(margin, Math.min(width - margin - cell, x + shiftAlong));
    }
    return { character, line: lineIndex, column, row, x, y, size: cell };
  }));
  return { width, height, direction, charactersPerLine: perLine, columns, rows, zigzag, placements };
}
