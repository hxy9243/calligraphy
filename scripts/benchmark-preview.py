"""Compare bounded glyph preparation with serial preview rendering (no network)."""
import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--text', default='春眠不觉晓，处处闻啼鸟。夜来风雨声，花落知多少')
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    from calligraphy.text.glyphs import resolve_glyphs
    resolve_glyphs(args.text, fetch_missing=False)  # Fail before any network-capable child.
    params = dict(text=args.text, style='kai', width=480, height=640,
                  font_size=100, fit=True, direction='vertical-rl', spacing=.18, punctuation='omit')
    expected = None
    for repeat in range(args.repeats):
        # Alternate order to reduce systematic warm-machine bias.
        for workers in ([1, 2] if repeat % 2 == 0 else [2, 1]):
            with tempfile.TemporaryDirectory(prefix='calligraphy-bench-') as folder:
                env = {**os.environ, 'CALLIGRAPHY_KAI_CACHE': folder + '/geometry.db',
                       'CALLIGRAPHY_PREVIEW_WORKERS': str(workers),
                       'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
                output = Path(folder) / 'preview.png'
                for state in ('cold', 'warm'):
                    start = time.perf_counter()
                    process = subprocess.Popen([sys.executable, '-m', 'backend.editor_preview', str(output)],
                        stdin=subprocess.PIPE, text=True, env=env, cwd=ROOT, start_new_session=True)
                    try:
                        process.communicate(json.dumps(params), timeout=120)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.communicate()
                        raise
                    if process.returncode:
                        raise subprocess.CalledProcessError(process.returncode, process.args)
                    seconds = time.perf_counter() - start
                    digest = hashlib.sha256(output.read_bytes()).hexdigest()
                    if expected is None:
                        expected = digest
                    if digest != expected:
                        raise AssertionError('Parallel/serial preview pixels changed')
                    print(json.dumps(dict(repeat=repeat, workers=workers, state=state,
                                          seconds=round(seconds, 4), png_sha256=digest)), flush=True)


if __name__ == '__main__':
    main()
