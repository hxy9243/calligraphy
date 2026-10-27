"""Fail closed on ephemeral storage overrides in volume-backed deployments.

CALLIGRAPHY_PERSISTENT_ROOT is opt-in. This validates path containment and write
access, not whether a provider has actually mounted a persistent volume there.
"""
import os
from pathlib import Path
import tempfile
from typing import Mapping, Optional


def _inside(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must be inside CALLIGRAPHY_PERSISTENT_ROOT")
    return resolved


def _check_writable_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    # NamedTemporaryFile deletes only its own unique probe, never user artifacts.
    with tempfile.NamedTemporaryFile(prefix=".calligraphy-storage-check-", dir=path) as probe:
        probe.write(b"storage-check")
        probe.flush()
        os.fsync(probe.fileno())


def check_storage(environ: Optional[Mapping[str, str]] = None) -> bool:
    env = os.environ if environ is None else environ
    configured_root = env.get("CALLIGRAPHY_PERSISTENT_ROOT")
    if not configured_root:
        return False
    root_path = Path(configured_root)
    if not root_path.is_absolute() or root_path.is_symlink() or not root_path.is_dir():
        raise ValueError("CALLIGRAPHY_PERSISTENT_ROOT must be an existing absolute directory, not a symlink")
    root = root_path.resolve()
    db_url = env.get("DATABASE_URL", "sqlite:///calligraphy.db")
    if not db_url.startswith("sqlite:///"):
        raise ValueError("Persistent Studio storage requires a sqlite:/// DATABASE_URL")
    db = _inside(Path(db_url[len("sqlite:///"):]), root, "Database path")
    outputs = _inside(Path(env.get("CALLIGRAPHY_OUTPUT_DIR", "outputs")), root, "Output path")
    artifact_directories = [
        _inside(outputs / name, root, f"{name} artifact path")
        for name in ("previews", "videos")
    ]
    if db == root or db.is_dir():
        raise ValueError("Database path must be a file inside the persistent root")
    # Resolve and validate every path before creating even an empty directory.
    _check_writable_directory(db.parent)
    _check_writable_directory(outputs)
    for directory in artifact_directories:
        _check_writable_directory(directory)
    if db.exists():
        # Confirm access without modifying existing database bytes or truncating it.
        with db.open("r+b"):
            pass
    return True


if __name__ == "__main__":
    try:
        check_storage()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Persistent storage validation failed: {error}") from error
