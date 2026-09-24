import characters from '../data/poem-characters.json' with { type: 'json' };

// Wang Wei, "Mountain Dwelling in Autumn" (山居秋暝), excerpt.
export const LINES = ['明月松间照', '清泉石上流'];
export const POEM = LINES.join('');

const INTRO = 1.15;
const GAP = 0.19;
const OUTRO = 1.65;
const STROKE_SECONDS = 0.175;
const CHARACTER_BASE_SECONDS = 0.70;

const schedule = [];
let cursor = INTRO;
for (const [line, text] of LINES.entries()) {
  for (const [row, character] of [...text].entries()) {
    const data = characters[character];
    if (!data || data.strokes.length !== data.medians.length) {
      throw new Error(`Missing or invalid stroke data for ${character}`);
    }
    const duration = CHARACTER_BASE_SECONDS + STROKE_SECONDS * data.strokes.length;
    schedule.push({ character, data, line, row, start: cursor, duration });
    cursor += duration + GAP;
  }
}
export const DURATION = Math.ceil(cursor + OUTRO);

const clamp = (n, low = 0, high = 1) => Math.max(low, Math.min(high, n));

function trace(points, fraction) {
  const lengths = points.slice(1).map((p, i) => Math.hypot(p[0] - points[i][0], p[1] - points[i][1]));
  let left = lengths.reduce((sum, len) => sum + len, 0) * clamp(fraction);
  const visited = [points[0]];
  for (let i = 0; i < lengths.length; i++) {
    if (left >= lengths[i]) {
      visited.push(points[i + 1]);
      left -= lengths[i];
    } else {
      const f = lengths[i] ? left / lengths[i] : 0;
      visited.push([
        points[i][0] + (points[i + 1][0] - points[i][0]) * f,
        points[i][1] + (points[i + 1][1] - points[i][1]) * f,
      ]);
      break;
    }
  }
  return `M ${visited.map(p => p.map(n => n.toFixed(2)).join(' ')).join(' L ')}`;
}

// Fixed grain, so exporting and seeking always show the same frame.
const grain = Array.from({ length: 650 }, (_, i) => {
  const x = (i * 191 + 37) % 1080;
  const y = (i * 353 + 81) % 1920;
  return `<circle cx="${x}" cy="${y}" r="${i % 8 ? 0.65 : 1.1}" fill="#695b48" opacity=".10"/>`;
}).join('');

function characterSVG(entry, t, index, expansion = 0) {
  if (t < entry.start) return '';
  const { data, line, row, start, duration } = entry;
  const x = line === 0 ? 687 : 306;
  const y = 276 + row * 275;
  const strokeTime = duration / data.strokes.length;
  const outlines = data.strokes.map((path, stroke) =>
    `<mask id="mask-${index}-${stroke}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280"><path d="${path}" fill="white" stroke="white" stroke-width="${expansion}" stroke-linejoin="round"/></mask>`
  ).join('');
  const marks = data.strokes.map((path, stroke) => {
    const progress = clamp((t - start - stroke * strokeTime) / strokeTime);
    if (progress <= 0) return '';
    if (progress >= 1) return `<path d="${path}" fill="url(#ink)" stroke="url(#ink)" stroke-width="${expansion}" stroke-linejoin="round"/>`;
    const median = trace(data.medians[stroke], progress);
    return `<g mask="url(#mask-${index}-${stroke})"><path d="${median}" fill="none" stroke="url(#ink)" stroke-width="${174 + expansion}" stroke-linecap="round" stroke-linejoin="round"/></g>`;
  }).join('');
  return `<defs>${outlines}</defs><g transform="translate(${x} ${y}) scale(.235)"><g transform="translate(0 900) scale(1 -1)">${marks}</g></g>`;
}

export function poemFrameSVG(time, options = {}) {
  const t = clamp(time, 0, DURATION);
  const count = schedule.filter(entry => t >= entry.start + entry.duration).length;
  const chars = schedule.map((entry, i) => characterSVG(entry, t, i, options.expansion || 0)).join('');
  const barWidth = Math.round(890 * t / DURATION);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">
    <defs>
      <linearGradient id="paper" x2=".8" y2="1"><stop stop-color="#f8f3e9"/><stop offset="1" stop-color="#eee5d4"/></linearGradient>
      <linearGradient id="ink" x1="0" x2=".8" y2="1"><stop stop-color="#38312b"/><stop offset=".6" stop-color="#1c1b19"/><stop offset="1" stop-color="#342e28"/></linearGradient>
    </defs>
    <rect width="1080" height="1920" fill="url(#paper)"/>
    ${grain}
    <path d="M 94 105 H 986 M 94 1764 H 986" fill="none" stroke="#a99c84" opacity=".55"/>
    <text x="96" y="158" font-family="Georgia,serif" font-size="29" letter-spacing="3" fill="#4c453b">MOUNTAIN DWELLING IN AUTUMN</text>
    <text x="98" y="210" font-family="Georgia,serif" font-size="18" letter-spacing="4" fill="#92836c">${options.yan ? `YAN-INSPIRED KAI · ${Number(options.speed || 1)}× SPEED` : 'A CALLIGRAPHY STUDY'}</text>
    <path d="M 600 242 V 1625 M 210 242 V 1625" stroke="#ac9d84" stroke-width="1" opacity=".11" stroke-dasharray="8 13"/>
    ${chars}
    <rect x="91" y="1624" width="57" height="57" fill="#aa4c3c" opacity=".90"/>
    <path d="M 103 1636 L 136 1669 M 136 1636 L 103 1669" stroke="#eddfd0" opacity=".6" stroke-width="2"/>
    <text x="169" y="1661" font-family="Georgia,serif" font-size="20" letter-spacing="4" fill="#81735f">WANG WEI · TANG DYNASTY</text>
    <text x="94" y="1816" font-family="Georgia,serif" font-size="18" letter-spacing="2" fill="#827560">BRIGHT MOON THROUGH THE PINES</text>
    <text x="94" y="1847" font-family="Georgia,serif" font-size="18" letter-spacing="2" fill="#827560">CLEAR SPRING OVER THE STONES</text>
    <text x="986" y="1847" text-anchor="end" font-family="Georgia,serif" font-size="19" fill="#827560">${String(count).padStart(2, '0')} / 10</text>
    <rect x="94" y="1882" width="890" height="2" fill="#cabda7" opacity=".65"/>
    <rect x="94" y="1882" width="${barWidth}" height="2" fill="#a04738"/>
  </svg>`;
}
