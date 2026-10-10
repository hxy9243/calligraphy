"""Owner-facing expiry metadata, using synthetic files and no rendering."""
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import Database


class JobRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(f"sqlite:///{self.tmp.name}/jobs.db")
        self.patch = patch("backend.database._DB_INSTANCE", self.db)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.config = patch.dict(os.environ, {"CALLIGRAPHY_RETENTION_SECONDS": "86400"})
        self.config.start()
        self.addCleanup(self.config.stop)
        self.owner = TestClient(app)
        self.addCleanup(self.owner.close)
        self.owner.get("/api/jobs")
        self.session = self.owner.cookies["calligraphy_session"]
        self.path = Path(self.tmp.name) / "synthetic.mp4"
        self.path.write_bytes(b"synthetic-video")
        self.now = time.time()
        self.completed = self.now - 300
        os.utime(self.path, (self.completed, self.completed))
        self.db.create_job("one", self.session, "render", "山水", "kai", {},
                           output_path=str(self.path), status="succeeded")
        with self.db._get_sqlite_conn() as conn:
            conn.execute("UPDATE jobs SET created_at = ?, completed_at = ? WHERE job_id = 'one'",
                         (self.iso(self.now - 90000), self.iso(self.completed)))

    @staticmethod
    def iso(timestamp):
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

    def summary(self):
        listing = self.owner.get("/api/jobs").json()
        job = next(j for j in listing["jobs"] if j["job_id"] == "one")
        detail = self.owner.get("/api/jobs/one").json()
        self.assertEqual(job["retention"], detail["retention"])
        return job["retention"]

    def test_default_retention_uses_completion_and_file_age_not_creation(self):
        summary = self.summary()
        self.assertAlmostEqual(summary["expires_at"], self.completed + 86400, places=4)
        self.assertEqual(summary["ordinary_expires_at"], summary["expires_at"])
        self.assertIsNone(summary["share_expires_at"])
        self.assertTrue(summary["output_available"])
        self.assertEqual(self.owner.get("/api/jobs").json()["retention_seconds"], 86400)

    def test_file_age_and_configured_cleanup_retention_are_honored(self):
        older_file = self.completed - 50
        os.utime(self.path, (older_file, older_file))
        for duration in (120, 172800):
            with patch.dict(os.environ, {"CALLIGRAPHY_RETENTION_SECONDS": str(duration)}):
                self.assertAlmostEqual(self.summary()["expires_at"], older_file + duration, places=4)
                self.assertEqual(self.owner.get("/api/jobs").json()["retention_seconds"], duration)

    def test_active_share_lease_is_reported_after_ordinary_expiry(self):
        expiry = self.now + 72 * 3600
        self.db.set_video_share("one", self.session, "digest", expiry)
        old = self.now - 2 * 86400
        os.utime(self.path, (old, old))
        with self.db._get_sqlite_conn() as conn:
            conn.execute("UPDATE jobs SET completed_at = ?, expires_at = ? WHERE job_id = 'one'",
                         (self.iso(old), self.iso(old)))
        summary = self.summary()
        self.assertEqual(summary["expires_at"], expiry)
        self.assertEqual(summary["share_expires_at"], expiry)
        self.assertLess(summary["ordinary_expires_at"], self.now)
        self.assertTrue(summary["output_available"])
        self.db.revoke_video_share("one", self.session)
        summary = self.summary()
        self.assertIsNone(summary["share_expires_at"])
        self.assertLess(summary["expires_at"], self.now)

    def test_expired_shares_and_ten_minute_exports_do_not_extend_retention(self):
        original = self.summary()
        exported = self.owner.post("/api/jobs/one/export-link")
        self.assertEqual(exported.status_code, 200)
        self.assertLessEqual(exported.json()["expires_at"], time.time() + 600)
        self.assertEqual(self.summary(), original)
        self.db.set_video_share("one", self.session, "expired", self.now - 1)
        self.assertEqual(self.summary(), original)

    def test_missing_artifact_failed_history_and_active_jobs_are_distinct(self):
        self.path.unlink()
        summary = self.summary()
        self.assertFalse(summary["output_available"])
        self.assertIsNotNone(summary["expires_at"])
        self.db.update_job("one", status="failed")
        summary = self.summary()
        self.assertIsNone(summary["output_available"])
        self.assertAlmostEqual(summary["expires_at"], self.completed + 86400, places=4)
        self.db.update_job("one", status="running")
        self.assertEqual(self.summary(), {"expires_at": None, "ordinary_expires_at": None,
                                         "share_expires_at": None, "output_available": None})

    def test_retention_metadata_is_session_scoped_and_does_not_expose_capabilities(self):
        expiry = self.now + 72 * 3600
        self.db.set_video_share("one", self.session, "sensitive-digest", expiry)
        self.assertNotIn("sensitive-digest", self.owner.get("/api/jobs").text)
        other = TestClient(app)
        self.addCleanup(other.close)
        self.assertEqual(other.get("/api/jobs").json()["jobs"], [])
        self.assertEqual(other.get("/api/jobs/one").status_code, 404)


if __name__ == "__main__":
    unittest.main()
