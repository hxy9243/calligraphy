import yanPreset from '../../assets/presets/yan-inspired.json' with { type: 'json' };
import { DURATION as yongDuration, frameSVG as yongFrameSVG } from './yong.mjs';
import { DURATION as poemDuration, poemFrameSVG } from './poem.mjs';

export const SCENES = Object.freeze({
  yong: Object.freeze({ name: 'yong', duration: yongDuration, width: 1080, height: 1080, frameSVG: yongFrameSVG }),
  poem: Object.freeze({ name: 'poem', duration: poemDuration, width: 1080, height: 1920, frameSVG: poemFrameSVG }),
});

export function sceneOptions({ style, speed = 1 } = {}) {
  if (!style) return {};
  if (style !== 'yan') throw new TypeError(`Unknown style: ${style}`);
  return { yan: true, speed, expansion: yanPreset.width_offset_px * 4 };
}

export function getScene(name) {
  const scene = SCENES[name];
  if (!scene) throw new TypeError(`Unknown scene: ${name}. Expected one of: ${Object.keys(SCENES).join(', ')}`);
  return scene;
}

export { yanPreset };
