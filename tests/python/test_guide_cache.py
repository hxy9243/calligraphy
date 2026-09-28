import json
import tempfile
import unittest
from pathlib import Path

from calligraphy.text import (
    GuideCache,
    get_default_guide_cache,
    resolve_glyphs,
)
from calligraphy.text.guides import compute_guide_hash


class GuideCacheTests(unittest.TestCase):
    def test_default_guide_cache_metadata(self):
        cache = get_default_guide_cache()
        self.assertEqual(cache.version, 1)
        self.assertEqual(cache.provider, "hanzi-writer-data")
        self.assertEqual(cache.dataset_version, "2.0.1")
        self.assertIn("Make Me a Hanzi", cache.license)
        self.assertGreaterEqual(len(cache), 11)
        self.assertIn("永", cache)
        self.assertIn("明", cache)

    def test_character_record_and_sha256(self):
        cache = get_default_guide_cache()
        record = cache.get("永")
        self.assertIsNotNone(record)
        self.assertEqual(record["character"], "永")
        self.assertIn("strokes", record)
        self.assertIn("medians", record)
        self.assertEqual(len(record["strokes"]), 5)
        self.assertEqual(len(record["medians"]), 5)
        # Verify sha256 integrity
        expected_hash = compute_guide_hash(record)
        self.assertEqual(record["sha256"], expected_hash)

    def test_put_and_negative_cache(self):
        cache = GuideCache()
        self.assertFalse(cache.has("中"))
        self.assertIsNone(cache.get("中"))
        cache.mark_missing("中")
        self.assertTrue(cache.is_negative("中"))

        # Put a valid character
        sample_record = {
            "strokes": ["M 0 0 L 100 100 Z"],
            "medians": [[[0, 0], [100, 100]]],
        }
        cache.put("中", sample_record)
        self.assertTrue(cache.has("中"))
        self.assertFalse(cache.is_negative("中"))
        stored = cache.get("中")
        self.assertEqual(stored["character"], "中")
        self.assertEqual(stored["sha256"], compute_guide_hash(sample_record))

    def test_save_and_load_roundtrip(self):
        cache = get_default_guide_cache()
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "guide_cache.json"
            cache.save(file_path)
            self.assertTrue(file_path.exists())

            loaded = GuideCache.load_from_file(file_path)
            self.assertEqual(loaded.version, cache.version)
            self.assertEqual(loaded.provider, cache.provider)
            self.assertEqual(loaded.dataset_version, cache.dataset_version)
            self.assertEqual(loaded.license, cache.license)
            self.assertEqual(len(loaded), len(cache))
            self.assertEqual(loaded.characters(), cache.characters())

    def test_resolve_glyphs_integration(self):
        resolved = resolve_glyphs("永明")
        self.assertIn("永", resolved)
        self.assertIn("明", resolved)
        self.assertEqual(len(resolved["永"]["strokes"]), 5)


if __name__ == "__main__":
    unittest.main()
