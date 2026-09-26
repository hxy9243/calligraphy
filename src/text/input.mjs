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
