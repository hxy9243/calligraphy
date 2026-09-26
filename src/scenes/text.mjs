import { clamp, tracePath } from '../geometry.mjs';
import { finiteNumber } from '../export/config.mjs';
import { parseText } from '../text/input.mjs';
import { bundledGlyphs, validateGlyph } from '../text/glyphs.mjs';
import { createTextPlan } from '../text/plan.mjs';
import yanPreset from '../../assets/presets/yan-inspired.json' with { type: 'json' };

const STYLES = Object.freeze({ kai: 0, yan: yanPreset.width_offset_px * 4 });

/** A deterministic text scene. Glyph preparation/network access is separate. */
export function createTextScene({ text, glyphs = bundledGlyphs, style = 'kai', layout = {}, timing = {}, punctuation = 'break' } = {}) {
  if (!Object.hasOwn(STYLES, style)) throw new TypeError(`Unknown template style: ${style}. Expected kai or yan.`);
  const parsed = parseText(text, { punctuation });
  const missing = parsed.uniqueCharacters.filter(character => !Object.hasOwn(glyphs, character));
  if (missing.length) throw new Error(`Missing glyphs: ${missing.join(' ')}. Prepare them with resolveGlyphs or supply a dictionary.`);
  const records = {};
  for (const character of parsed.uniqueCharacters) {
    const data = validateGlyph(character, glyphs[character]);
    records[character] = { strokes: [...data.strokes], medians: data.medians.map(points => points.map(point => [...point])) };
  }
  const plan = createTextPlan({ text,
    strokeCounts: Object.fromEntries(Object.entries(records).map(([character, data]) => [character, data.strokes.length])),
    layout, timing, punctuation });
  const { schedule, duration, strokeSeconds, width, height } = plan;
  const expansion = STYLES[style];
  function frameSVG(time) {
    const t = clamp(finiteNumber(time, 'time'), 0, duration);
    const marks = schedule.map(entry => {
      if (t <= entry.start) return '';
      const data = records[entry.character];
      const strokes = data.strokes.map((path, i) => {
        const progress = t >= entry.end ? 1 : clamp((t - entry.start - i * strokeSeconds) / strokeSeconds);
        if (progress <= 0) return '';
        if (progress >= 1) return `<path d="${path}" fill="#25221f" stroke="#25221f" stroke-width="${expansion}" stroke-linejoin="round"/>`;
        const id = `text-${entry.index}-${i}`;
        return `<defs><mask id="${id}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280"><path d="${path}" fill="white" stroke="white" stroke-width="${expansion}" stroke-linejoin="round"/></mask></defs><path d="${tracePath(data.medians[i], progress)}" mask="url(#${id})" fill="none" stroke="#25221f" stroke-width="${174 + expansion}" stroke-linecap="round" stroke-linejoin="round"/>`;
      }).join('');
      // Canonical Hanzi geometry: x in [0,1024], y in [-124,900]. Inset 4%.
      return `<g data-character="${entry.character}" transform="translate(${entry.x + entry.size * .04} ${entry.y + entry.size * .04}) scale(${entry.size * .92 / 1024})"><g transform="translate(0 900) scale(1 -1)">${strokes}</g></g>`;
    }).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="100%" height="100%" fill="#f8f3e9"/>${marks}</svg>`;
  }
  return Object.freeze({ name: 'text', text, style, width, height, duration,
    plan, schedule, omitted: plan.omitted, frameSVG });
}
