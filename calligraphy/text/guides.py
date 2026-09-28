"""Character guide cache and versioned provider metadata."""
import hashlib
import json
from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def compute_guide_hash(record: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of stroke outlines and median paths."""
    canonical = json.dumps(
        {
            "strokes": record.get("strokes", []),
            "medians": record.get("medians", []),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GuideCache:
    """Persistent, versioned character guide cache for Hanzi stroke/median records."""

    DEFAULT_VERSION = 1
    DEFAULT_PROVIDER = "hanzi-writer-data"
    DEFAULT_DATASET_VERSION = "2.0.1"
    DEFAULT_LICENSE = "LGPL-3.0 / Make Me a Hanzi"

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        source_path: Optional[Union[str, Path]] = None,
    ):
        self.source_path = Path(source_path) if source_path else None
        if data is not None:
            self._version = data.get("version", self.DEFAULT_VERSION)
            self._provider = data.get("provider", self.DEFAULT_PROVIDER)
            self._dataset_version = data.get("dataset_version", self.DEFAULT_DATASET_VERSION)
            self._license = data.get("license", self.DEFAULT_LICENSE)
            self._characters: Dict[str, Dict[str, Any]] = dict(data.get("characters", {}))
        else:
            self._version = self.DEFAULT_VERSION
            self._provider = self.DEFAULT_PROVIDER
            self._dataset_version = self.DEFAULT_DATASET_VERSION
            self._license = self.DEFAULT_LICENSE
            self._characters = {}
        self._negative_cache: set[str] = set()

    @property
    def version(self) -> int:
        return self._version

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def dataset_version(self) -> str:
        return self._dataset_version

    @property
    def license(self) -> str:
        return self._license

    def __len__(self) -> int:
        return len(self._characters)

    def __contains__(self, character: str) -> bool:
        return character in self._characters

    def has(self, character: str) -> bool:
        return character in self._characters

    def characters(self) -> List[str]:
        return sorted(self._characters.keys())

    def get(self, character: str) -> Optional[Dict[str, Any]]:
        """Retrieve record for character."""
        return self._characters.get(character)

    def put(self, character: str, record: Dict[str, Any]) -> None:
        """Insert or update a validated character guide in cache."""
        entry = {
            "character": character,
            "sha256": record.get("sha256") or compute_guide_hash(record),
            "strokes": record["strokes"],
            "medians": record["medians"],
        }
        if "radStrokes" in record:
            entry["radStrokes"] = record["radStrokes"]
        self._characters[character] = entry
        self._negative_cache.discard(character)

    def mark_missing(self, character: str) -> None:
        """Mark character in negative cache."""
        self._negative_cache.add(character)

    def is_negative(self, character: str) -> bool:
        return character in self._negative_cache

    def to_dict(self) -> Dict[str, Any]:
        """Export cache dictionary with metadata."""
        return {
            "version": self._version,
            "provider": self._provider,
            "dataset_version": self._dataset_version,
            "license": self._license,
            "characters": self._characters,
        }

    def save(self, path: Optional[Union[str, Path]] = None) -> Path:
        """Save guide cache to JSON file."""
        target = Path(path) if path else self.source_path
        if not target:
            raise ValueError("No target path provided for saving GuideCache")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return target

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> "GuideCache":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls(data=data, source_path=p)

    @classmethod
    def load_default(cls) -> "GuideCache":
        """Load bundled default guide cache from package assets or repo root."""
        try:
            data_file = files("calligraphy").joinpath("assets/data/guide_cache.json")
            content = data_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return cls(data=data)
        except Exception:
            root = Path(__file__).resolve().parent.parent.parent / "assets" / "data" / "guide_cache.json"
            if root.exists():
                return cls.load_from_file(root)
            # Fallback to empty if not found
            return cls()


_DEFAULT_GUIDE_CACHE: Optional[GuideCache] = None


def get_default_guide_cache() -> GuideCache:
    global _DEFAULT_GUIDE_CACHE
    if _DEFAULT_GUIDE_CACHE is None:
        _DEFAULT_GUIDE_CACHE = GuideCache.load_default()
    return _DEFAULT_GUIDE_CACHE
