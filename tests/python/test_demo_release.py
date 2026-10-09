"""Public admission, private fonts and recovery regressions."""
import os
import hashlib
import json
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import AdmissionError, Database
from backend.worker import BackgroundTaskRunner, execute_job_bounded, cleanup_expired_outputs
from backend.editor_preview import render_pixels
from backend.public_fonts import private_catalog, font_sample, validate_style
from deploy.check_fonts import restore_fonts


class DemoReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.url = f"sqlite:///{Path(self.temp.name) / 'jobs.db'}"
        self.db = Database(self.url)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        p = patch("backend.app.get_db", return_value=self.db)
        p.start(); self.addCleanup(p.stop)
        p = patch("backend.app.get_runner")
        p.start(); self.addCleanup(p.stop)
        self.client.cookies.set("calligraphy_session", "user-a")

    def create(self, db, job_id, session="user-a"):
        return db.create_job(job_id, session, "preview", "永", "kai", {}, status="succeeded", admit=True)

    def test_concurrent_admission_is_exactly_three_and_survives_reopen_and_deletion(self):
        def submit(i):
            try:
                self.create(Database(self.url), str(i))
                return True
            except AdmissionError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            accepted = list(pool.map(submit, range(8)))
        self.assertEqual(sum(accepted), 3)
        for job in self.db.list_jobs("user-a"):
            self.db.delete_history_job(job["job_id"], "user-a")
        with self.assertRaises(AdmissionError):
            self.create(Database(self.url), "after-reopen")
        self.create(self.db, "other", "user-b")

    def test_window_expires_at_sixty_seconds(self):
        with patch("backend.database.time.time", return_value=1000):
            for i in range(3): self.create(self.db, str(i))
        with patch("backend.database.time.time", return_value=1059):
            with self.assertRaises(AdmissionError) as denied:
                self.create(self.db, "denied")
            self.assertEqual(denied.exception.retry_after, 1)
        with patch("backend.database.time.time", return_value=1060):
            self.create(self.db, "new-window")

    def test_preview_and_video_share_budget_but_identical_active_video_is_free(self):
        def preview(job, db):
            output = Path(self.temp.name) / 'preview.svg'
            output.write_text('<svg/>')
            db.update_job(job['job_id'], status='succeeded', output_path=str(output), completed=True)
            return True
        payload = {"text": "永", "style": "kai"}
        with patch("backend.app.execute_job", side_effect=preview):
            self.assertEqual(self.client.post("/api/previews", json=payload).status_code, 200)
        first = self.client.post("/api/renders", json=payload)
        self.assertEqual(first.status_code, 202)
        second = self.client.post("/api/renders", json={**payload, "text": "明"})
        self.assertEqual(second.status_code, 202)
        repeat = self.client.post("/api/renders", json=payload)
        self.assertEqual(repeat.json()["job_id"], first.json()["job_id"])
        denied = self.client.post("/api/renders", json={**payload, "text": "月"})
        self.assertEqual(denied.status_code, 429)
        self.assertIn("Retry-After", denied.headers)
        self.assertEqual(len(self.db.list_jobs("user-a")), 3)

    def test_invalid_requests_and_full_queue_do_not_consume_budget(self):
        for override in ({"width": 100000}, {"height": -1}, {"width": 65}, {"style": "unknown-style"}, {"style": "shutifang-liugongquan-kai"}):
            res = self.client.post("/api/renders", json={"text": "永", **override})
            self.assertIn(res.status_code, (400, 422), res.text)
        with patch.dict(os.environ, {"CALLIGRAPHY_MAX_ACTIVE_JOBS": "1"}):
            self.db.create_job("active", "other", "render", "永", "kai", {})
            self.assertEqual(self.client.post("/api/renders", json={"text": "永"}).status_code, 429)
            self.db.update_job("active", status="failed", completed=True)
            self.assertEqual(self.client.post("/api/renders", json={"text": "永"}).status_code, 202)

    def test_font_bytes_are_unreachable_and_samples_are_only_pixels(self):
        for path in ("/fonts/", "/fonts/MaShanZheng.ttf", "/data/fonts/MaShanZheng.ttf", "/fonts/%2e%2e/data/fonts/MaShanZheng.ttf"):
            self.assertEqual(self.client.get(path).status_code, 404)
        sample = self.client.get("/api/font-samples/mashanzheng-kai")
        self.assertEqual(sample.status_code, 200)
        self.assertEqual(sample.headers["content-type"], "image/png")
        self.assertTrue(sample.content.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(self.client.get("/api/font-samples/shutifang-liugongquan-kai").status_code, 404)
        self.assertNotIn("@font-face", self.client.get("/app.js").text)

    def test_full_demo_catalog_keeps_paths_private_and_bundles_every_source(self):
        with patch.dict(os.environ, {"CALLIGRAPHY_DEMO_ALL_FONTS": "1"}):
            catalog = self.client.get('/api/font-catalog').json()
            self.assertEqual(len(catalog), len(private_catalog()))
            self.assertIn('aa shoujin', [e['id'] for e in catalog])
            self.assertIn('shutifang-liugongquan-kai', [e['id'] for e in catalog])
            for entry in catalog:
                for key in ('file_path', 'license_path', 'source_url', 'download_url'):
                    self.assertNotIn(key, entry)
            for entry in private_catalog():
                root = Path(__file__).resolve().parents[2]
                self.assertEqual(bool(entry['is_downloaded']), (root / entry['file_path']).is_file())
                self.assertTrue((root / entry['license_path']).is_file())
            self.assertEqual(self.client.get('/fonts/AaShouJin.ttf').status_code, 404)

    def test_absent_private_font_inputs_are_unavailable_in_source_only_checkouts(self):
        root = Path(self.temp.name) / 'source-only'
        (root / 'data').mkdir(parents=True)
        (root / 'data/calligraphy_fonts.json').write_text(json.dumps([
            {'id': 'private-source-fixture', 'is_downloaded': 1, 'file_path': 'data/fonts/private.ttf'}
        ]))
        with patch('backend.public_fonts.ROOT', root):
            self.assertEqual(private_catalog()[0]['is_downloaded'], 0)
            with self.assertRaises(ValueError): validate_style('private-source-fixture')

    def test_editor_pixels_use_selected_font_and_direction_without_export_budget(self):
        params = dict(text='永\n明月', style='mashanzheng', width=240, height=320,
                      font_size=48, fit=True, direction='vertical-rl', spacing=.18, punctuation='omit')
        vertical = render_pixels(params)
        horizontal = render_pixels({**params, 'direction': 'horizontal-lr'})
        other_font = render_pixels({**params, 'style': 'longcang'})
        self.assertNotEqual(vertical, horizontal)
        self.assertNotEqual(vertical, other_font)
        with patch('backend.app.editor_preview', return_value=vertical):
            for i in range(5):
                response = self.client.post('/api/editor-preview', json={**params, 'text': '永' * (i + 1)})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['content-type'], 'image/png')
        self.assertEqual(self.db.list_jobs('user-a'), [])
        for i in range(3): self.create(self.db, f'export-{i}')
        self.assertEqual(self.client.post('/api/editor-preview', json={**params, 'width': 641}).status_code, 422)

    def test_private_volume_fonts_are_verified_and_missing_sources_fail_startup(self):
        root = Path(self.temp.name) / 'app'
        sources = Path(self.temp.name) / 'private-sources'
        (root / 'deploy').mkdir(parents=True)
        sources.mkdir()
        payload = b'private source font fixture'
        (sources / 'demo.ttf').write_bytes(payload)
        (root / 'deploy/font_assets.json').write_text(json.dumps({'demo.ttf': hashlib.sha256(payload).hexdigest()}))
        restore_fonts(root, sources)
        self.assertEqual((root / 'data/fonts/demo.ttf').read_bytes(), payload)
        (root / 'data/fonts/demo.ttf').write_bytes(b'corrupted')
        restore_fonts(root, sources)
        self.assertEqual((root / 'data/fonts/demo.ttf').read_bytes(), payload)
        (root / 'data/fonts/demo.ttf').unlink()
        (sources / 'demo.ttf').write_bytes(b'wrong version')
        with self.assertRaises(RuntimeError): restore_fonts(root, sources)

    def test_restart_fails_interrupted_work_and_preserves_queue_and_success(self):
        for state in ("queued", "rendering", "running", "succeeded"):
            self.db.create_job(state, "user-a", "render", "永", "kai", {}, status=state)
        self.assertEqual(Database(self.url).recover_interrupted_jobs(), 2)
        for state in ("rendering", "running"):
            self.assertEqual(self.db.get_job(state)["status"], "failed")
            self.assertIsNotNone(self.db.get_job(state)["completed_at"])
        self.assertEqual(self.db.claim_next_job()["job_id"], "queued")
        self.assertEqual(self.db.get_job("succeeded")["status"], "succeeded")

    def test_second_instance_cannot_recover_live_worker_jobs(self):
        runner = BackgroundTaskRunner(self.db)
        runner.start()
        self.addCleanup(runner.stop)
        self.db.create_job("live", "user-a", "preview", "永", "kai", {}, status="rendering")
        with self.assertRaises(RuntimeError):
            BackgroundTaskRunner(Database(self.url)).start()
        self.assertEqual(self.db.get_job("live")["status"], "rendering")

    def test_deadline_kills_process_group_and_records_retryable_failure(self):
        job = self.db.create_job("deadline", "user-a", "render", "永", "kai", {})
        actual_popen = subprocess.Popen
        child = None
        def stalled_process(*args, **kwargs):
            nonlocal child
            child = actual_popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
            return child
        with patch.dict(os.environ, {"CALLIGRAPHY_ISOLATE_JOBS": "1", "CALLIGRAPHY_JOB_TIMEOUT_SECONDS": "1"}), patch("backend.worker.subprocess.Popen", side_effect=stalled_process):
            self.assertFalse(execute_job_bounded(job, self.db))
        self.assertEqual(child.returncode, -signal.SIGKILL)
        self.assertEqual(self.db.get_job("deadline")["status"], "failed")
        self.assertIn("time limit", self.db.get_job("deadline")["error_message"])

    def test_cleanup_removes_expired_history_and_orphans_but_keeps_recent_files(self):
        root = Path(self.temp.name) / 'outputs'
        (root / 'videos').mkdir(parents=True)
        old = root / 'videos/orphan.mp4'; old.write_bytes(b'old')
        os.utime(old, (time.time()-90000,)*2)
        recent = root / 'videos/recent.mp4'; recent.write_bytes(b'new')
        self.db.create_job('old', 'user-a', 'render', '永', 'kai', {}, status='succeeded')
        with self.db._get_sqlite_conn() as conn:
            conn.execute("UPDATE jobs SET completed_at = '2000-01-01T00:00:00+00:00'")
        with patch.dict(os.environ, {'CALLIGRAPHY_OUTPUT_DIR': str(root)}):
            cleanup_expired_outputs(self.db)
        self.assertIsNone(self.db.get_job('old'))
        self.assertFalse(old.exists()); self.assertTrue(recent.exists())

    def test_cross_origin_mutations_are_rejected(self):
        response = self.client.post('/api/renders', json={'text': '永'}, headers={'Origin': 'https://other.example'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.list_jobs('user-a'), [])
