import { spawn } from 'node:child_process';
import { access } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

export const CONTACT_STYLES = Object.freeze(['lishu', 'liu', 'yan-contact']);

async function pythonExecutable(override) {
  if (override || process.env.CALLIGRAPHY_PYTHON || process.env.PYTHON) return override || process.env.CALLIGRAPHY_PYTHON || process.env.PYTHON;
  const local = fileURLToPath(new URL('../../.venv/bin/python', import.meta.url));
  try { await access(local); return local; } catch { return 'python3'; }
}

async function invoke(style, { request, pythonPath } = {}) {
  if (!CONTACT_STYLES.includes(style)) throw new TypeError(`Unknown contact style: ${style}`);
  const python = await pythonExecutable(pythonPath);
  return new Promise((resolve, reject) => {
    const args = ['-m', 'calligraphy.contact_renderer', '--style', style];
    if (!request) args.push('--describe');
    const child = spawn(python, args, { stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', inputError;
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-16384); });
    child.stdin.on('error', error => { inputError = error; });
    child.once('error', error => reject(new Error(`Cannot start contact renderer (${python}): ${error.message}. Install the Python package and set CALLIGRAPHY_PYTHON if needed.`)));
    child.once('close', code => {
      if (code !== 0) {
        reject(new Error(`Contact renderer exited ${code}: ${stderr.trim() || inputError?.message || 'no diagnostic'}. Use a Python environment with calligraphy-engine installed.`));
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

export function renderContactStyle({ style, plan, output, time, fps = 24, speed = 1, ffmpeg = process.env.FFMPEG || 'ffmpeg', pythonPath }) {
  return invoke(style, { pythonPath, request: { plan, output, time, fps, speed, ffmpeg } });
}
