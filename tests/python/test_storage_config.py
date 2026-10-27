"""Deployment storage guard without a real provider volume or production data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from deploy.check_storage import check_storage


class StorageConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "volume"
        self.root.mkdir()
        self.env = {
            "CALLIGRAPHY_PERSISTENT_ROOT": str(self.root),
            "DATABASE_URL": f"sqlite:///{self.root}/db/jobs.db",
            "CALLIGRAPHY_OUTPUT_DIR": str(self.root / "outputs"),
        }

    def test_unconfigured_local_development_skips_guard(self):
        self.assertFalse(check_storage({}))

    def test_valid_storage_is_writable_without_leaving_probe_files(self):
        self.assertTrue(check_storage(self.env))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["db", "outputs"])
        self.assertEqual(list((self.root / "db").iterdir()), [])
        self.assertEqual(sorted(p.name for p in (self.root / "outputs").iterdir()), ["previews", "videos"])
        self.assertEqual(list((self.root / "outputs" / "previews").iterdir()), [])
        self.assertEqual(list((self.root / "outputs" / "videos").iterdir()), [])

    def test_existing_database_and_artwork_bytes_are_untouched(self):
        db = self.root / "db" / "jobs.db"
        db.parent.mkdir()
        db.write_bytes(b"existing database")
        output = self.root / "outputs"
        output.mkdir()
        work = output / "work.mp4"
        work.write_bytes(b"existing artwork")
        self.assertTrue(check_storage(self.env))
        self.assertEqual(db.read_bytes(), b"existing database")
        self.assertEqual(work.read_bytes(), b"existing artwork")

    def test_database_and_outputs_must_both_be_inside_root(self):
        outside = Path(self.tmp.name) / "ephemeral"
        for key, value in (("DATABASE_URL", f"sqlite:///{outside}/jobs.db"),
                           ("CALLIGRAPHY_OUTPUT_DIR", str(outside))):
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_storage({**self.env, key: value})
            self.assertFalse(outside.exists())
            self.assertEqual(list(self.root.iterdir()), [])

    def test_symlink_escape_is_rejected(self):
        outside = Path(self.tmp.name) / "ephemeral"
        outside.mkdir()
        (self.root / "link").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            check_storage({**self.env, "CALLIGRAPHY_OUTPUT_DIR": str(self.root / "link" / "outputs")})
        self.assertEqual(list(outside.iterdir()), [])

    def test_artifact_subdirectory_symlink_escape_rejected_before_side_effects(self):
        outside = Path(self.tmp.name) / "ephemeral"
        outside.mkdir()
        outputs = self.root / "outputs"
        outputs.mkdir()
        for child in ("previews", "videos"):
            with self.subTest(child=child):
                link = outputs / child
                link.symlink_to(outside, target_is_directory=True)
                with self.assertRaises(ValueError):
                    check_storage(self.env)
                self.assertFalse((self.root / "db").exists())
                self.assertEqual(list(outside.iterdir()), [])
                self.assertEqual(list(outputs.iterdir()), [link])
                link.unlink()

    def test_root_requires_existing_absolute_non_symlink_directory(self):
        for root in ("relative", str(self.root / "missing")):
            with self.subTest(root=root), self.assertRaises(ValueError):
                check_storage({**self.env, "CALLIGRAPHY_PERSISTENT_ROOT": root})
        alias = Path(self.tmp.name) / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            check_storage({**self.env, "CALLIGRAPHY_PERSISTENT_ROOT": str(alias)})

    def test_unsupported_database_and_directory_database_rejected(self):
        for url in ("postgresql://localhost/jobs", "sqlite:///:memory:", f"sqlite:///{self.root}"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                check_storage({**self.env, "DATABASE_URL": url})

    def test_unwritable_probe_aborts_startup(self):
        with patch("deploy.check_storage.tempfile.NamedTemporaryFile", side_effect=PermissionError("read only")):
            with self.assertRaises(PermissionError):
                check_storage(self.env)


if __name__ == "__main__":
    unittest.main()
