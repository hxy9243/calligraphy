import yong from '../../assets/data/yong.json' with { type: 'json' };
import poem from '../../assets/data/poem-characters.json' with { type: 'json' };
import { parseText } from './input.mjs';

export const GLYPH_DATA_VERSION = '2.0.1';
// These records are inputs only; scene construction copies the geometry it uses.
export const bundledGlyphs = Object.freeze({ ...poem, 永: yong });

export function validateGlyph(character, glyph) {
  if (!glyph || !Array.isArray(glyph.strokes) || !glyph.strokes.length || glyph.strokes.length > 128 ||
      !Array.isArray(glyph.medians) || glyph.medians.length !== glyph.strokes.length) {
    throw new TypeError(`Invalid glyph ${character}: expected 1–128 matching strokes and medians`);
  }
  for (let i = 0; i < glyph.strokes.length; i++) {
    const path = glyph.strokes[i];
    const median = glyph.medians[i];
    if (typeof path !== 'string' || !/^[Mm]/.test(path.trim()) || !/^[MmZzLlHhVvCcSsQqTtAa\d\s.,+\-eE]+$/.test(path)) {
      throw new TypeError(`Invalid glyph ${character}: stroke ${i + 1} must be SVG path data`);
    }
    if (!Array.isArray(median) || median.length < 2 || !median.every(point =>
      Array.isArray(point) && point.length === 2 && point.every(Number.isFinite))) {
      throw new TypeError(`Invalid glyph ${character}: median ${i + 1} needs finite [x,y] points`);
    }
  }
  return glyph;
}

/** Explicit preparation step; scene rendering itself never performs network I/O. */
export async function resolveGlyphs(text, { glyphs = bundledGlyphs, fetchMissing = false,
  fetchImpl = globalThis.fetch, punctuation = 'break' } = {}) {
  const { uniqueCharacters } = parseText(text, { punctuation });
  const result = {};
  const missing = [];
  for (const character of uniqueCharacters) {
    if (Object.hasOwn(glyphs, character)) result[character] = validateGlyph(character, glyphs[character]);
    else missing.push(character);
  }
  if (missing.length && !fetchMissing) throw new Error(`Missing glyphs: ${missing.join(' ')}. Supply glyph data or explicitly enable fetching.`);
  if (missing.length && typeof fetchImpl !== 'function') throw new TypeError('fetch is unavailable');
  // Bound concurrent requests and fail without mutating the caller's dictionary.
  for (let offset = 0; offset < missing.length; offset += 4) {
    const batch = await Promise.all(missing.slice(offset, offset + 4).map(async character => {
      const url = `https://cdn.jsdelivr.net/npm/hanzi-writer-data@${GLYPH_DATA_VERSION}/${encodeURIComponent(character)}.json`;
      const response = await fetchImpl(url, { signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error(`Could not fetch glyph ${character}: HTTP ${response.status}`);
      return [character, validateGlyph(character, await response.json())];
    }));
    Object.assign(result, Object.fromEntries(batch));
  }
  return result;
}
