import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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

    @patch('backend.app.registered_styles', return_value=[
        {'style': name, 'prepared': 1} for name in ('mashanzheng', 'i-yan-kai', 'qiji-kai')
    ])
    def test_list_styles(self, registered):
        res = self.client.get("/api/styles")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("styles", data)
        style_ids = [s["id"] for s in data["styles"]]
        self.assertIn("kai", style_ids)
        self.assertEqual(next(s for s in data["styles"] if s["id"] == "kai")["type"], "stroke_ir")
        self.assertIn("yan", style_ids)
        # Verify fixed collection contact styles are removed
        self.assertNotIn("yan-contact", style_ids)
        self.assertNotIn("lishu", style_ids)
        self.assertNotIn("liu", style_ids)
        for s in data["styles"]:
            self.assertNotEqual(s.get("type"), "contact")
        # Verify newly added fonts
        self.assertIn("mashanzheng", style_ids)
        self.assertIn("i-yan-kai", style_ids)
        self.assertIn("qiji-kai", style_ids)
        registered.assert_called_once()

    def test_convert_script(self):
        res_trad = self.client.post("/api/convert-script", json={"text": "春眠不觉晓，处处闻啼鸟", "target": "trad"})
        self.assertEqual(res_trad.status_code, 200)
        data_trad = res_trad.json()
        self.assertEqual(data_trad["text"], "春眠不覺曉，處處聞啼鳥")

        res_simp = self.client.post("/api/convert-script", json={"text": "明月松間照，清泉石上流", "target": "simp"})
        self.assertEqual(res_simp.status_code, 200)
        data_simp = res_simp.json()
        self.assertEqual(data_simp["text"], "明月松间照，清泉石上流")

    def test_font_catalog_and_static_fonts(self):
        res = self.client.get("/api/font-catalog")
        self.assertEqual(res.status_code, 200)
        catalog = res.json()
        self.assertIsInstance(catalog, list)
        self.assertGreater(len(catalog), 10)
        catalog_ids = [f["id"] for f in catalog]
        self.assertIn("mashanzheng-kai", catalog_ids)
        self.assertIn("i-yan-kai", catalog_ids)
        self.assertIn("tw-kai", catalog_ids)
        # Verify newly integrated traditional styles
        self.assertIn("tw-sung", catalog_ids)
        self.assertIn("genryu-min", catalog_ids)
        self.assertIn("genwan-min", catalog_ids)
        self.assertIn("cwtex-fangsong", catalog_ids)
        self.assertIn("hanwang-shinsu", catalog_ids)
        # Verify removed styles are absent
        for removed_id in (
            "hanwang-pen-kai",
            "bpmf-zihi-kai",
            "hanwang-boldpen-xingkai",
            "hanwang-wave-kai",
        ):
            self.assertNotIn(removed_id, catalog_ids)
        # The full local inventory restores the existing Kan Da Yan source font.
        self.assertIn("hanwang-kandayan", catalog_ids)

        # Font bytes stay private even when their exact filenames are known.
        for filename in ("MaShanZheng.ttf", "TW-Sung.ttf", "GenRyuMin-Regular.otf", "cwTeXFangSong.ttf"):
            self.assertEqual(self.client.get(f"/fonts/{filename}").status_code, 404)
        self.assertTrue(all("file_path" not in entry and "download_url" not in entry for entry in catalog))
        self.assertNotIn("shutifang-liugongquan-kai", catalog_ids)

    def test_delete_history_is_session_scoped_and_only_allows_terminal_jobs(self):
        self.client.get("/api/styles")
        session = self.client.cookies.get("calligraphy_session")
        output = Path(self.temp_dir.name) / "preview.svg"
        output.write_text("<svg/>")
        for state in ("succeeded", "failed", "queued", "rendering", "running"):
            self.db.create_job(state, session, "preview", "永", "kai", {},
                               output_path=str(output), status=state)
        other = TestClient(app)
        self.assertEqual(other.delete("/api/jobs/succeeded").status_code, 404)
        self.assertIsNotNone(self.db.get_job("succeeded"))
        for state in ("queued", "rendering", "running"):
            self.assertEqual(self.client.delete(f"/api/jobs/{state}").status_code, 409)
            self.assertIsNotNone(self.db.get_job(state))
        for state in ("succeeded", "failed"):
            self.assertEqual(self.client.delete(f"/api/jobs/{state}").status_code, 204)
            self.assertIsNone(self.db.get_job(state))
            self.assertEqual(self.client.get(f"/api/jobs/{state}").status_code, 404)
            self.assertEqual(self.client.get(f"/api/jobs/{state}/image").status_code, 404)
            self.assertEqual(self.client.delete(f"/api/jobs/{state}").status_code, 404)
        self.assertEqual({j["job_id"] for j in self.client.get("/api/jobs").json()["jobs"]},
                         {"queued", "rendering", "running"})
        self.assertTrue(output.exists())

    def test_session_cookie_created(self):
        res = self.client.get("/api/styles")
        self.assertEqual(res.status_code, 200)
        self.assertIn("calligraphy_session", res.cookies)

    def test_preview_generation(self):
        res = self.client.post("/api/previews", json={"text": "永", "style": "kai", "spacing": 0.25})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("job_id", data)
        self.assertIn("preview_url", data)
        self.assertIn("svg", data)
        self.assertTrue(data["svg"].startswith("<svg"))
        self.assertIn('data-engine="kai-fitted"', data["svg"])

        # Fetch preview image
        img_res = self.client.get(data["preview_url"])
        self.assertEqual(img_res.status_code, 200)
        self.assertIn(img_res.headers["content-type"], ("image/svg+xml", "image/png"))
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
        self.assertIsNotNone(status_data["video_url"])

        # Stream inline video
        video_res = self.client.get(f"/api/jobs/{job_id}/video")
        self.assertEqual(video_res.status_code, 200)
        self.assertEqual(video_res.headers["content-type"], "video/mp4")
        self.assertGreater(len(video_res.content), 1000)

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

    def test_character_limit_expansion_and_error_message(self):
        # 256 characters total (including newlines, each line <= 20 chars) is accepted
        valid_text = "\n".join(["永" * 16 for _ in range(15)] + ["永"])
        self.assertEqual(len(valid_text), 256)
        res_valid = self.client.post("/api/renders", json={"text": valid_text, "style": "kai"})
        self.assertEqual(res_valid.status_code, 202)

        # 257 characters exceeds limit and returns clear 400 error message
        excess_text = valid_text + "永"
        self.assertEqual(len(excess_text), 257)
        res_excess = self.client.post("/api/renders", json={"text": excess_text, "style": "kai"})
        self.assertEqual(res_excess.status_code, 400)
        data = res_excess.json()
        self.assertIn("detail", data)
        self.assertIn("256", data["detail"])

        # Preview endpoint also enforces the limit
        res_prev_excess = self.client.post("/api/previews", json={"text": excess_text, "style": "kai"})
        self.assertEqual(res_prev_excess.status_code, 400)
        prev_data = res_prev_excess.json()
        self.assertIn("detail", prev_data)
        self.assertIn("256", prev_data["detail"])

    def test_single_line_limit(self):
        # Line with <= 20 characters is accepted
        res_valid = self.client.post("/api/previews", json={"text": "永" * 20, "style": "kai"})
        self.assertEqual(res_valid.status_code, 200)

        # Single line with 21 characters is rejected with 400
        res_excess = self.client.post("/api/previews", json={"text": "永" * 21, "style": "kai"})
        self.assertEqual(res_excess.status_code, 400)
        data = res_excess.json()
        self.assertIn("20", data["detail"])

    def test_punctuation_option_default_omit(self):
        # By default, punctuation is ignored/omitted
        res_omit = self.client.post(
            "/api/previews",
            json={"text": "明，月。", "style": "kai"},
        )
        self.assertEqual(res_omit.status_code, 200)
        svg_omit = res_omit.json().get("svg", "")
        self.assertIn('data-character="明"', svg_omit)
        self.assertIn('data-character="月"', svg_omit)

        # Explicit break punctuation
        res_break = self.client.post(
            "/api/previews",
            json={"text": "明，月。", "style": "kai", "punctuation": "break"},
        )
        self.assertEqual(res_break.status_code, 200)

        # Video render with default punctuation omit
        res_render = self.client.post(
            "/api/renders",
            json={"text": "明，月。", "style": "kai"},
        )
        self.assertEqual(res_render.status_code, 202)
        job = self.db.get_job(res_render.json()["job_id"])
        self.assertEqual(job["params"].get("punctuation"), "omit")


if __name__ == "__main__":
    unittest.main()
