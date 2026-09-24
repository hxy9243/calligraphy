import { writeFile } from 'node:fs/promises';

// Fetch only the characters required by a given text, never the full corpus.
const [text, destination = 'data/poem-characters.json'] = process.argv.slice(2);
if (!text) {
  console.error('Usage: node scripts/fetch-characters.mjs "明月松间照清泉石上流" [output.json]');
  process.exit(1);
}
const chars = [...new Set([...text].filter(char => /\p{Script=Han}/u.test(char)))];
const entries = await Promise.all(chars.map(async char => {
  const url = `https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${encodeURIComponent(char)}.json`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`No stroke data for ${char}: HTTP ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data.strokes) || data.strokes.length !== data.medians?.length) {
    throw new Error(`Invalid stroke data for ${char}`);
  }
  return [char, data];
}));
await writeFile(destination, JSON.stringify(Object.fromEntries(entries), null, 2) + '\n');
console.log(`Wrote ${entries.length} characters to ${destination}`);
