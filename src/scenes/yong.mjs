import character from '../../assets/data/yong.json' with { type: 'json' };
import { clamp, tracePolyline } from '../geometry.mjs';

export const DURATION = 8.0;
const timings = [
  { start: 1.00, duration: 0.55 },
  { start: 1.77, duration: 1.43 },
  { start: 3.42, duration: 1.30 },
  { start: 4.98, duration: 0.95 },
  { start: 6.14, duration: 1.11 },
];

// A tiny deterministic grain. No flicker when seeking or exporting.
const grain = Array.from({ length: 470 }, (_, i) => {
  const x = (i * 191 + 37) % 1080;
  const y = (i * 353 + 81) % 1080;
  const r = i % 9 === 0 ? 1.05 : 0.55;
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="#86765e" opacity=".12"/>`;
}).join('');

export function frameSVG(time) {
  const t = clamp(time, 0, DURATION);
  const defs = character.strokes.map((outline, i) =>
    `<clipPath id="outline-${i}"><path d="${outline}"/></clipPath>`
  ).join('');

  const strokes = character.strokes.map((outline, i) => {
    const { start, duration } = timings[i];
    const p = clamp((t - start) / duration);
    if (p <= 0) return '';
    if (p >= 1) return `<path d="${outline}" fill="url(#ink)"/>`;

    // The enlarged median is clipped to the real outline, preserving its shape.
    const { path: d, tip } = tracePolyline(character.medians[i], p);
    const tipMark = `<ellipse cx="${tip[0]}" cy="${tip[1]}" rx="42" ry="34" fill="#25221f" opacity=".16"/>`;
    return `<g clip-path="url(#outline-${i})">
      <path d="${d}" fill="none" stroke="url(#ink)" stroke-width="160" stroke-linecap="round" stroke-linejoin="round"/>
      ${tipMark}
    </g>`;
  }).join('');

  const number = t < 1 ? '—' : String(Math.min(5, timings.filter(s => t >= s.start).length)).padStart(2, '0');

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1080" width="1080" height="1080">
    <defs>
      <linearGradient id="paper" x2=".8" y2="1"><stop stop-color="#f6f1e7"/><stop offset="1" stop-color="#ece4d4"/></linearGradient>
      <linearGradient id="ink" x1=".1" y1="0" x2=".85" y2="1"><stop stop-color="#302b28"/><stop offset=".6" stop-color="#191917"/><stop offset="1" stop-color="#37312a"/></linearGradient>
      ${defs}
    </defs>
    <rect width="1080" height="1080" fill="url(#paper)"/>
    ${grain}
    <path d="M 67 79 H 1013 M 67 1008 H 1013" stroke="#b6a993" opacity=".55" stroke-width="1"/>
    <text x="70" y="122" font-family="Georgia,serif" font-size="32" letter-spacing="5" fill="#514a40">YONG</text>
    <text x="1010" y="121" text-anchor="end" font-family="Georgia,serif" font-size="17" letter-spacing="3" fill="#867766">KAI · BRUSH STUDY</text>
    <rect x="147" y="179" width="786" height="786" fill="none" stroke="#aa9c85" opacity=".20"/>
    <path d="M 540 180 V 964 M 148 572 H 932" stroke="#aa9c85" opacity=".13" stroke-width="1" stroke-dasharray="7 10"/>
    <g transform="translate(146 180) scale(.768)">
      <g transform="translate(0 900) scale(1 -1)">${strokes}</g>
    </g>
    <text x="70" y="1040" font-family="Georgia,serif" font-size="17" letter-spacing="3" fill="#857768">EIGHT PRINCIPLES · ONE CHARACTER</text>
    <text x="1010" y="1040" text-anchor="end" font-family="Georgia,serif" font-size="18" fill="#857768">${number} / 05</text>
  </svg>`;
}
