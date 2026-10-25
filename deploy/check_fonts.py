"""Restore private volume font inputs into the container and verify their hashes."""
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent


def restore_fonts(root=ROOT, sources=None):
    custom_sources = sources is not None
    source_candidates = [Path(sources or os.environ.get('CALLIGRAPHY_FONT_SOURCE_DIR', '/data/font-sources'))]
    if not custom_sources:
        source_candidates.append(root.parent.parent / 'calligraphy' / 'data/fonts')
        source_candidates.append(root.parent / 'calligraphy' / 'data/fonts')
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
            found_source = None
            for candidate_dir in source_candidates:
                source = candidate_dir / name
                if matches(source):
                    found_source = source
                    break
            if not found_source:
                raise RuntimeError(f'Missing or mismatched private font asset: {name}. Seed /data/font-sources before deploying.')
            shutil.copyfile(found_source, path)
        if not matches(path):
            raise RuntimeError(f'Font asset verification failed: {name}')

    # Restore raster samples if available in main repo
    samples_target = root / 'data/font_samples'
    if not samples_target.exists():
        for candidate_dir in source_candidates:
            samples_source = candidate_dir.parent / 'font_samples'
            if samples_source.is_dir():
                shutil.copytree(samples_source, samples_target)
                break

    print(f'Verified {len(manifest)} private font source files.', flush=True)


if __name__ == '__main__':
    restore_fonts()
