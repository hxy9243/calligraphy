import { spawn } from 'node:child_process';
import { access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

export const CONTACT_STYLES = Object.freeze(['lishu', 'liu', 'yan-contact']);

async function pythonExecutable(override) {
  if (override || process.env.CALLIGRAPHY_PYTHON || process.env.PYTHON) return override || process.env.CALLIGRAPHY_PYTHON || process.env.PYTHON;
  const local = fileURLToPath(new URL('../../.venv/bin/python', import.meta.url));
  try { await access(local); return local; } catch { return 'python3'; }
}

async function invoke(style, { request, pythonPath, prepare = false, list = false } = {}) {
  if (!list && (typeof style !== 'string' || !/^[a-z][a-z0-9 -]{0,79}$/.test(style))) throw new TypeError(`Invalid contact style: ${style}`);
  const python = await pythonExecutable(pythonPath);
  return new Promise((resolve, reject) => {
    const args = ['-m', 'calligraphy.contact_renderer'];
    if (list) args.push('--list');
    else args.push('--style', style);
    if (prepare) args.push('--prepare');
    else if (!request && !list) args.push('--describe');
    const child = spawn(python, args, { stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', progressBuffer = '', inputError;
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => {
      stderr = (stderr + chunk).slice(-16384);
      if (prepare) {
        progressBuffer += chunk;
        const lines = progressBuffer.split('\n');
        progressBuffer = lines.pop();
        // Stream progress once; report errors once when the process exits.
        for (const line of lines) if (line.startsWith('Prepared ')) process.stderr.write(`${line}\n`);
      }
    });
    child.stdin.on('error', error => { inputError = error; });
    child.once('error', error => reject(new Error(`Cannot start contact renderer (${python}): ${error.message}. Install the Python package and set CALLIGRAPHY_PYTHON if needed.`)));
    child.once('close', code => {
      if (code !== 0) {
        const detail = stderr.trim().split(/\r?\n/).at(-1) || inputError?.message || 'no diagnostic';
        const hint = /ModuleNotFoundError:|No module named/.test(stderr)
          ? ' Use a Python environment with calligraphy-engine and its dependencies installed.' : '';
        reject(new Error(`Contact renderer exited ${code}: ${detail}${hint}`));
      } else {
        try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Contact renderer returned invalid JSON')); }
      }
    });
    child.stdin.end(request ? JSON.stringify(request) : undefined);
  });
}

export function describeContactStyle(style, options = {}) {
  return invoke(style, options);
}

export function renderContactStyle({ style, plan, output, time, fps = 24, speed = 1, ffmpeg = process.env.FFMPEG || 'ffmpeg', pythonPath, workers = 8 }) {
  return invoke(style, { pythonPath, request: { plan, output, time, fps, speed, ffmpeg, workers } });
}

export function prepareFontStyle({ style, glyphs, fontPath, licensePath, source, pythonPath, workers = 8 }) {
  return invoke(style, { pythonPath, prepare: true, request: { glyphs, fontPath, licensePath, source, workers } });
}

export function listContactStyles(options = {}) {
  return invoke(undefined, { ...options, list: true });
}
