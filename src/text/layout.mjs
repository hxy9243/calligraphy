import { finiteNumber, positiveInteger } from '../export/config.mjs';

/** One fitted page; explicit lines remain separate and long lines wrap. */
export function layoutText(lines, { width = 1080, height = 1440, direction = 'vertical-rl',
  charactersPerLine, margin = Math.min(width, height) * 0.07, gap = 0.18 } = {}) {
  width = positiveInteger(width, 'width', { minimum: 64 });
  height = positiveInteger(height, 'height', { minimum: 64 });
  if (width > 8192 || height > 8192) throw new RangeError('Page dimensions must not exceed 8192');
  if (!['vertical-rl', 'horizontal-lr'].includes(direction)) throw new TypeError('direction must be vertical-rl or horizontal-lr');
  margin = finiteNumber(margin, 'margin', { minimum: 0 });
  gap = finiteNumber(gap, 'gap', { minimum: 0, maximum: 2 });
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
  const cell = Math.min(availableWidth / (columns + (columns - 1) * gap), availableHeight / (rows + (rows - 1) * gap));
  if (cell < 16) throw new RangeError('Text is too dense for this page; use a larger page or fewer characters');
  const left = (width - cell * (columns + (columns - 1) * gap)) / 2;
  const top = (height - cell * (rows + (rows - 1) * gap)) / 2;
  const placements = wrapped.flatMap((line, lineIndex) => line.map((character, index) => {
    const column = vertical ? columns - 1 - lineIndex : index;
    const row = vertical ? index : lineIndex;
    return { character, line: lineIndex, column, row, x: left + column * cell * (1 + gap), y: top + row * cell * (1 + gap), size: cell };
  }));
  return { width, height, direction, charactersPerLine: perLine, columns, rows, placements };
}
