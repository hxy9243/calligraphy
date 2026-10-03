import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from calligraphy.artifact_cache import ArtifactCache
from calligraphy.engine_metadata import engine_metadata


class ArtifactCacheTests(unittest.TestCase):
    def test_startup_import_export_preserves_original_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = Path(__file__).resolve().parents[2] / 'examples/kai-stroke-ir/fixtures/chun-xiao-programs.json'
            original = json.loads(source.read_text())
            cache = ArtifactCache(root / 'geometry.db', [('spring-dawn', source)])
            self.assertEqual(cache.get('spring-dawn'), original)
            cache = ArtifactCache(root / 'geometry.db', [('spring-dawn', source)])
            self.assertEqual(len(cache.list_versions()), 1)
            output = root / 'snapshot.json'
            cache.export_json('spring-dawn', output)
            self.assertEqual(json.loads(output.read_text()), original)
            # The exported snapshot still passes the actual replay loader.
            import importlib.util
            spec = importlib.util.spec_from_file_location('replay', source.parents[1] / 'render.py')
            replay = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(replay)
            self.assertEqual(replay.load_bundle(output), original)
            self.assertEqual(replay.load_bundle(output, root / 'startup.db'), original)
            self.assertEqual(ArtifactCache(root / 'startup.db').get('kai-writing-scene'), original)

    def test_versions_are_explicit_and_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'geometry.db'
            cache = ArtifactCache(path)
            first = {'schemaVersion': 1, 'engine': {'engine_code_commit': 'old'}}
            second = {'schemaVersion': 1, 'engine': {'engine_code_commit': 'new'}}
            a, b = cache.put('glyph', first), cache.put('glyph', second)
            self.assertNotEqual(a, b)
            with self.assertRaisesRegex(ValueError, 'Multiple'):
                cache.get('glyph')
            self.assertEqual(cache.get('glyph', a), first)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('UPDATE geometry_artifacts SET document_json=? WHERE content_id=?', ('{}', a))
            with self.assertRaisesRegex(ValueError, 'checksum'):
                cache.get('glyph', a)
            with self.assertRaises(ValueError):
                cache.put('bad', {'schemaVersion': 1, 'value': float('nan')})

    def test_engine_identity_has_source_hash_and_safe_missing_git(self):
        metadata = engine_metadata('kai-fitted')
        self.assertEqual(metadata['engine_version'], 'kai-fitted-v1')
        self.assertEqual(len(metadata['engine_source_sha256']), 64)
        with patch('calligraphy.engine_metadata.subprocess.check_output', side_effect=OSError):
            unknown = engine_metadata('font-contact')
        self.assertIsNone(unknown['engine_code_commit'])
        self.assertIsNone(unknown['engine_code_dirty'])
        self.assertEqual(unknown['engine_source_sha256'], metadata['engine_source_sha256'])
