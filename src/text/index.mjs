// Browser-safe entry point: no Sharp, filesystem or child-process imports.
export { createTextScene } from '../scenes/text.mjs';
export { resolveGlyphs, bundledGlyphs, GLYPH_DATA_VERSION } from './glyphs.mjs';
export { parseText } from './input.mjs';
export { createTextPlan } from './plan.mjs';
