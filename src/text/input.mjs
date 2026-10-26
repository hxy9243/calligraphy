const HAN = /\p{Script=Han}/u;
const PUNCTUATION = /[，。！？、；：,.!?;:「」『』（）()“”‘’《》〈〉…—·]/u;

/** Parse writing order without converting simplified/traditional characters. */
export function parseText(text, { punctuation = 'break' } = {}) {
  if (typeof text !== 'string' || !text.trim()) throw new TypeError('text must be a non-empty string');
  if (!['break', 'omit'].includes(punctuation)) throw new TypeError('punctuation must be break or omit');
  const lines = [[]];
  const omitted = new Set();
  const unsupported = new Set();
  const lineBreak = () => { if (lines.at(-1).length) lines.push([]); };
  for (const character of text.replace(/\r\n?/g, '\n')) {
    if (character === '\n') lineBreak();
    else if (/\s/u.test(character)) omitted.add(character);
    else if (HAN.test(character)) lines.at(-1).push(character);
    else if (PUNCTUATION.test(character)) {
      omitted.add(character);
      if (punctuation === 'break') lineBreak();
    } else unsupported.add(character);
  }
  if (unsupported.size) throw new TypeError(`Unsupported characters: ${[...unsupported].join(' ')}. Use Han text, whitespace and supported punctuation.`);
  const nonempty = lines.filter(line => line.length);
  const characters = nonempty.flat();
  if (!characters.length) throw new TypeError('text must contain at least one Han character');
  if (characters.length > 512) throw new RangeError('text exceeds the 512-character single-page limit');
  return { lines: nonempty, characters, uniqueCharacters: [...new Set(characters)], omitted: [...omitted] };
}

const STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
const BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];

/**
 * Generate a dynamic Chinese Ganzhi year and seasonal calligraphy inscription based on date.
 * Four seasons divide by solar terms: Lichun (~Feb 4), Lixia (~May 5), Liqiu (~Aug 7), Lidong (~Nov 7).
 */
export function getDefaultInscription(date = new Date(), script = 'trad') {
  const y = date.getFullYear();
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const md = m * 100 + d;

  let effectiveYear = y;
  let season = '春';
  if (md < 204) {
    effectiveYear = y - 1;
    season = '冬';
  } else if (md < 505) {
    effectiveYear = y;
    season = '春';
  } else if (md < 807) {
    effectiveYear = y;
    season = '夏';
  } else if (md < 1107) {
    effectiveYear = y;
    season = '秋';
  } else {
    effectiveYear = y;
    season = '冬';
  }

  const offset = ((effectiveYear - 4) % 60 + 60) % 60;
  const stem = STEMS[offset % 10];
  const branch = BRANCHES[offset % 12];
  const suffix = (script === 'trad') ? '墨韻書法生成' : '墨韵书法生成';
  return `${stem}${branch}年${season} ${suffix}`;
}

