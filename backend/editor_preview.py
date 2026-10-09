"""Short-lived, bounded raster typesetting for the editor, without export jobs."""
import io
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .public_fonts import ROOT, private_catalog, validate_style
from .style_catalog import downloaded_catalog_entry

_SLOT = threading.Lock()


def _cgroup_directories(controller):
    """Inspect the process's cgroup and ancestors, including non-namespaced hosts."""
    root = Path('/sys/fs/cgroup')
    directories = {root, root / controller}
    try:
        memberships = Path('/proc/self/cgroup').read_text().splitlines()
    except OSError:
        memberships = []
    for membership in memberships:
        try:
            _, controllers, relative = membership.split(':', 2)
        except ValueError:
            continue
        if controllers and controller not in controllers.split(','):
            continue
        relative = Path(relative.lstrip('/'))
        if '..' in relative.parts:
            continue
        base = root / controllers if controllers else root
        current = base / relative
        while current != base:
            directories.add(current)
            current = current.parent
        directories.add(base)
    return directories


def glyph_worker_count():
    """At most two processes within the existing single-preview admission slot."""
    try:
        workers = max(1, min(2, int(os.environ.get('CALLIGRAPHY_PREVIEW_WORKERS', '2'))))
    except ValueError:
        workers = 1
    cpus = os.cpu_count() or 1
    if hasattr(os, 'sched_getaffinity'):
        try:
            cpus = min(cpus, len(os.sched_getaffinity(0)))
        except OSError:
            pass
    workers = min(workers, max(1, cpus))
    for directory in _cgroup_directories('cpu'):
        try:
            quota, period = (directory / 'cpu.max').read_text().split()
            if quota != 'max':
                workers = min(workers, max(1, int(quota) // int(period)))
        except (OSError, ValueError, ZeroDivisionError):
            pass
        try:
            quota = int((directory / 'cpu.cfs_quota_us').read_text())
            period = int((directory / 'cpu.cfs_period_us').read_text())
            if quota > 0:
                workers = min(workers, max(1, quota // period))
        except (OSError, ValueError, ZeroDivisionError):
            pass
    for directory in _cgroup_directories('memory'):
        for name in ('memory.max', 'memory.limit_in_bytes'):
            try:
                limit = int((directory / name).read_text())
                # Reserve 256 MiB for the parent and 256 MiB per fitting child.
                workers = min(workers, max(1, (limit - 256 * 1024**2) // (256 * 1024**2)))
            except (OSError, ValueError):
                pass
    return workers


def render_pixels(params):
    style = validate_style(params['style'])
    width, height = params['width'], params['height']
    if style in {'kai', 'yan'}:
        from calligraphy.renderer import create_scene
        from calligraphy.spec import SceneSpec
        scene = create_scene(SceneSpec(text=params['text'], style=style,
            layout={'width': width, 'height': height, 'direction': params['direction'], 'gap': params['spacing']},
            punctuation=params['punctuation']), fetch_missing=True, glyph_workers=glyph_worker_count())
        duration = scene.duration if hasattr(scene, 'duration') else scene.plan.duration
        image = scene.frame(duration)
    else:
        entry = downloaded_catalog_entry(private_catalog(), style)
        if not entry:
            raise ValueError('No bundled source font for this style.')
        path = (ROOT / entry['file_path']).resolve()
        if not path.is_relative_to(ROOT / 'data/fonts'):
            raise ValueError('Invalid font asset')
        # Explicit lines are columns in vertical writing; punctuation can break lines.
        lines = params.get('lines')
        if lines is None:
            from calligraphy.text.input import parse_text
            lines = parse_text(params['text'], punctuation=params['punctuation'])['lines']
        lines = [line for line in lines if line]
        if not lines:
            raise ValueError('请输入汉字 / Please enter Chinese characters.')
        from fontTools.ttLib import TTFont
        with TTFont(str(path), fontNumber=0, lazy=True) as source:
            cmap = source.getBestCmap() or {}
            missing = sorted({char for line in lines for char in line if ord(char) not in cmap})
        if missing:
            raise ValueError('当前字体缺少字符 / Missing font glyphs: ' + ' '.join(missing))
        vertical = params['direction'] == 'vertical-rl'
        max_chars = max(len(line) for line in lines)
        columns, rows = (len(lines), max_chars) if vertical else (max_chars, len(lines))
        size = params['font_size']
        step = 1 + params['spacing']
        if params['fit']:
            size = min(size, (width - 40) / (1 + (columns - 1) * step),
                       (height - 40) / (1 + (rows - 1) * step))
        size = max(1, math.floor(size))
        font = ImageFont.truetype(str(path), size)
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        x0 = (width - size * (1 + (columns - 1) * step)) / 2
        y0 = (height - size * (1 + (rows - 1) * step)) / 2
        for line_no, line in enumerate(lines):
            for char_no, char in enumerate(line):
                col, row = (columns - 1 - line_no, char_no) if vertical else (char_no, line_no)
                box = font.getbbox(char)
                x = x0 + col * size * step + (size - box[2] + box[0]) / 2 - box[0]
                y = y0 + row * size * step + (size - box[3] + box[1]) / 2 - box[1]
                draw.text((x, y), char, font=font, fill='#1c1b18')
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


@lru_cache(maxsize=32)
def cached_preview(payload):
    # A child process bounds font parsing / built-in rendering time and memory lifetime.
    with tempfile.TemporaryDirectory(prefix='calligraphy-editor-') as temp:
        target = Path(temp) / 'preview.png'
        process = subprocess.Popen([sys.executable, '-m', 'backend.editor_preview', str(target)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, start_new_session=True,
            env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
                 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'})
        try:
            _, error = process.communicate(payload.encode(), timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise TimeoutError('预览超时，请缩短文本 / Preview timed out; please shorten the text.')
        if process.returncode:
            raise ValueError(error.decode(errors='replace')[-500:])
        return target.read_bytes()


def editor_preview(params):
    if not _SLOT.acquire(blocking=False):
        raise BlockingIOError('预览服务繁忙，请稍后重试 / Preview busy; please retry.')
    try:
        return cached_preview(json.dumps(params, sort_keys=True, ensure_ascii=False))
    finally:
        _SLOT.release()


if __name__ == '__main__':
    try:
        Path(sys.argv[1]).write_bytes(render_pixels(json.load(sys.stdin)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
