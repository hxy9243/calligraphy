"""Restore private volume font inputs into the container and verify their hashes."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent


def restore_fonts(root=ROOT, sources=None):
    sources = Path(sources or os.environ.get('CALLIGRAPHY_FONT_SOURCE_DIR', '/data/font-sources'))
    target = root / 'data/fonts'
    target.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / 'deploy/font_assets.json').read_text())
    for name, expected in manifest.items():
        if Path(name).name != name:
            raise ValueError('Invalid font asset name')
        path = target / name
        def matches(candidate):
            if not candidate.is_file():
                return False
            with candidate.open('rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest() == expected
        if not matches(path):
            source = sources / name
            if not matches(source):
                raise RuntimeError(f'Missing or mismatched private font asset: {name}. Seed /data/font-sources before deploying.')
            shutil.copyfile(source, path)
        if not matches(path):
            raise RuntimeError(f'Font asset verification failed: {name}')
    print(f'Verified {len(manifest)} private font source files.', flush=True)


if __name__ == '__main__':
    restore_fonts()
