import { finiteNumber, positiveInteger, positiveNumber } from '../export/config.mjs';
import { parseText } from './input.mjs';
import { layoutText } from './layout.mjs';

/** Geometry-independent page and timing contract for current/future renderers. */
export function createTextPlan({ text, strokeCounts, layout = {}, timing = {}, punctuation = 'break' } = {}) {
  const parsed = parseText(text, { punctuation });
  if (!strokeCounts || typeof strokeCounts !== 'object') throw new TypeError('strokeCounts must map each character to a positive stroke count');
  const missing = parsed.uniqueCharacters.filter(character => !Object.hasOwn(strokeCounts, character));
  if (missing.length) throw new Error(`Missing stroke counts: ${missing.join(' ')}`);
  const counts = Object.fromEntries(parsed.uniqueCharacters.map(character => {
    const count = positiveInteger(strokeCounts[character], `stroke count for ${character}`);
    if (count > 128) throw new RangeError(`Stroke count for ${character} exceeds 128`);
    return [character, count];
  }));
  const page = layoutText(parsed.lines, layout);
  const intro = finiteNumber(timing.intro ?? 0.5, 'intro', { minimum: 0, maximum: 60 });
  const outro = finiteNumber(timing.outro ?? 1, 'outro', { minimum: 0, maximum: 60 });
  const gap = finiteNumber(timing.characterGap ?? 0.15, 'characterGap', { minimum: 0, maximum: 60 });
  const strokeSeconds = positiveNumber(timing.strokeSeconds ?? 0.18, 'strokeSeconds', { maximum: 60 });
  let cursor = intro;
  const schedule = page.placements.map((placement, index) => {
    const strokeCount = counts[placement.character];
    const duration = strokeCount * strokeSeconds;
    const entry = Object.freeze({ ...placement, index, strokeCount, start: cursor, duration, end: cursor + duration });
    cursor += duration + (index < page.placements.length - 1 ? gap : 0);
    return entry;
  });
  return Object.freeze({ schemaVersion: 1, text, width: page.width, height: page.height,
    direction: page.direction, strokeSeconds, duration: cursor + outro,
    schedule: Object.freeze(schedule), omitted: Object.freeze(parsed.omitted) });
}
