"""Identify the implementation producing geometry without guessing old provenance."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import subprocess

ENGINE_VERSIONS = {'font-contact': 'font-contact-v1', 'kai-fitted': 'kai-fitted-v1',
                   'kai-replay': 'kai-stroke-ir/0.2'}


def engine_metadata(engine_type):
    """Record package, Git revision and source hash; Git may be unavailable in wheels."""
    engine_version = ENGINE_VERSIONS[engine_type]
    package = Path(__file__).resolve().parent
    digest = sha256()
    # Include all reusable engine code, including uncommitted and untracked files.
    for path in sorted(package.rglob('*.py')):
        digest.update(path.relative_to(package).as_posix().encode() + b'\0')
        digest.update(path.read_bytes())
    commit, dirty = None, None
    # Do not accidentally identify a site-packages directory by an unrelated repo.
    root = package.parent
    if (root / '.git').exists():
        try:
            commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                             stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
            dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--',
                                                  'calligraphy', 'pyproject.toml'],
                                                 stderr=subprocess.DEVNULL, text=True, timeout=5).strip())
        except (OSError, subprocess.SubprocessError):
            commit, dirty = None, None
    try:
        package_version = version('calligraphy-engine')
    except PackageNotFoundError:
        package_version = None
    return {'engine_type': engine_type, 'engine_version': engine_version,
            'engine_code_commit': commit, 'engine_code_dirty': dirty,
            'engine_source_sha256': digest.hexdigest(), 'package_version': package_version,
            'prepared_at': datetime.now(timezone.utc).isoformat()}
