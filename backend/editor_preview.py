"""Short-lived, bounded raster typesetting for the editor, without export jobs."""
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
from functools import lru_cache

from PIL import Image

from .public_fonts import ROOT, private_catalog, validate_style
from .style_catalog import downloaded_catalog_entry
from .composition import scene_spec_from_params

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
    spec = scene_spec_from_params(params['text'], style, params)
    if style in {'kai', 'yan'}:
        from calligraphy.renderer import create_scene
        scene = create_scene(spec, fetch_missing=True, glyph_workers=glyph_worker_count())
        duration = scene.duration if hasattr(scene, 'duration') else scene.plan.duration
        image = scene.frame(duration)
    else:
        entry = downloaded_catalog_entry(private_catalog(), style)
        if not entry:
            raise ValueError('No bundled source font for this style.')
        path = (ROOT / entry['file_path']).resolve()
        if not path.is_relative_to(ROOT / 'data/fonts'):
            raise ValueError('Invalid font asset')
        # Keep this path lightweight: do not fit/register font strokes on edits.
        # Use the export plan, normalized source masks, ink and patch placement;
        # the inferred brush texture of the eventual export may still differ.
        from types import SimpleNamespace
        from calligraphy.font_pipeline import target_masks
        from calligraphy.font_layers import FontLayerScene
        from calligraphy.spec import RenderPlan
        from calligraphy.styled_contact_scene import paste_patch
        plan = RenderPlan.create(spec, {char: 1 for char in spec.unique_characters})
        painter = SimpleNamespace(appearance=spec.appearance, transforms=spec.transforms)
        size = plan.schedule[0]['size']
        patches = {char: FontLayerScene._create_patch(painter, mask, size)
                   for char, mask in target_masks(path, spec.unique_characters)}
        image = Image.new('RGB', (plan.width, plan.height), spec.appearance.paper_color)
        for placement in plan.schedule:
            paste_patch(image, placement, patches[placement['character']])
    # Rasterize the same logical page as exports, then downsample for transport.
    # Scaling geometry first changes wrapping, rounding, margins and brush ink.
    image.thumbnail((640, 640), Image.Resampling.LANCZOS)
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
