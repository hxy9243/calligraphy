import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Database, get_db
from backend.worker import execute_job


class BackendApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_file = Path(self.temp_dir.name) / "test.db"
        self.db = Database(f"sqlite:///{db_file}")
        # Override global DB instance for tests
        import backend.database as db_mod
        import backend.app as app_mod
        db_mod._DB_INSTANCE = self.db
        app_mod._DB_INSTANCE = self.db

        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_styles(self):
        res = self.client.get("/api/styles")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("styles", data)
        style_ids = [s["id"] for s in data["styles"]]
        self.assertIn("kai", style_ids)
        self.assertIn("yan", style_ids)

    def test_session_cookie_created(self):
        res = self.client.get("/api/styles")
        self.assertEqual(res.status_code, 200)
        self.assertIn("calligraphy_session", res.cookies)

    def test_preview_generation(self):
        res = self.client.post("/api/previews", json={"text": "永", "style": "kai"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("job_id", data)
        self.assertIn("preview_url", data)

        # Fetch preview image
        img_res = self.client.get(data["preview_url"])
        self.assertEqual(img_res.status_code, 200)
        self.assertEqual(img_res.headers["content-type"], "image/png")
        self.assertGreater(len(img_res.content), 100)

    def test_render_submission_and_download(self):
        res = self.client.post(
            "/api/renders",
            json={"text": "永", "style": "kai", "fps": 12, "speed": 2.0},
        )
        self.assertEqual(res.status_code, 202)
        job_data = res.json()
        job_id = job_data["job_id"]
        self.assertEqual(job_data["status"], "queued")

        # Execute queued job
        job = self.db.get_job(job_id)
        self.assertIsNotNone(job)
        success = execute_job(job, self.db)
        self.assertTrue(success)

        # Check job status via API
        status_res = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertEqual(status_data["status"], "succeeded")
        self.assertEqual(status_data["progress"], 1.0)
        self.assertIsNotNone(status_data["download_url"])

        # Download video
        dl_res = self.client.get(f"/api/jobs/{job_id}/download")
        self.assertEqual(dl_res.status_code, 200)
        self.assertEqual(dl_res.headers["content-type"], "video/mp4")
        self.assertGreater(len(dl_res.content), 1000)

    def test_session_isolation(self):
        # Session A creates a render job
        res_a = self.client.post(
            "/api/renders",
            json={"text": "明", "style": "kai"},
        )
        job_id = res_a.json()["job_id"]

        # Session B attempts to access Session A's job
        client_b = TestClient(app)
        res_b = client_b.get(f"/api/jobs/{job_id}")
        self.assertEqual(res_b.status_code, 404)

        res_b_dl = client_b.get(f"/api/jobs/{job_id}/download")
        self.assertEqual(res_b_dl.status_code, 404)


if __name__ == "__main__":
    unittest.main()
