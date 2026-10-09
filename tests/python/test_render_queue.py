"""Hermetic SQLite queue/API regressions: no glyph fitting or video encoding."""
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Database


PARAMS = {"fps": 24, "speed": 1.0, "spacing": 0.18}


class RenderQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_url = f"sqlite:///{Path(self.temp_dir.name) / 'jobs.db'}"
        self.db = Database(self.db_url)

    def enqueue(self, job_id, session="session-a", **overrides):
        request = dict(text="永", style="kai", params=PARAMS.copy())
        request.update(overrides)
        return self.db.enqueue_render(job_id, session, **request)

    def test_active_render_deduplication_and_terminal_retries(self):
        first = self.enqueue("first")
        self.assertEqual(first["status"], "queued")
        for status in ("queued", "rendering", "running"):
            with self.subTest(status=status):
                self.db.update_job("first", status=status)
                duplicate = self.enqueue(f"duplicate-{status}")
                self.assertEqual(duplicate["job_id"], "first")
                self.assertEqual(duplicate["status"], status)
        self.assertEqual(len(self.db.list_jobs("session-a")), 1)

        self.db.update_job("first", status="failed", completed=True)
        retry = self.enqueue("retry")
        self.assertEqual(retry["job_id"], "retry")
        self.db.update_job("retry", status="succeeded", completed=True)
        again = self.enqueue("again")
        self.assertEqual(again["job_id"], "again")
        self.assertEqual(len(self.db.list_jobs("session-a")), 3)

    def test_identity_includes_session_text_style_and_all_parameters(self):
        self.enqueue("first")
        self.assertEqual(self.enqueue("other-user", session="session-b")["job_id"], "other-user")
        variants = [
            {"text": "明"}, {"style": "yan"},
            *({"params": {**PARAMS, name: value}} for name, value in (
                ("fps", 30), ("speed", 2.0), ("spacing", 0.25),
                ("direction", "horizontal-lr"), ("width", 1080),
            )),
        ]
        for index, change in enumerate(variants):
            with self.subTest(change=change):
                job_id = f"variant-{index}"
                self.assertEqual(self.enqueue(job_id, **change)["job_id"], job_id)

    def test_existing_unsorted_json_and_numeric_defaults_merge(self):
        # Existing databases serialized parameters in request order.
        self.db.create_job("old", "session-a", "render", "永", "kai", PARAMS)
        conn = self.db._get_sqlite_conn()
        with conn:
            conn.execute(
                "UPDATE jobs SET params_json = ? WHERE job_id = 'old'",
                ('{"speed":1,"spacing":0.18,"fps":24}',),
            )
        duplicate = self.enqueue("duplicate", params=dict(reversed(list(PARAMS.items()))))
        self.assertEqual(duplicate["job_id"], "old")

    def test_legacy_missing_direction_matches_only_default_vertical(self):
        self.db.create_job("legacy", "session-a", "render", "永", "kai", PARAMS)
        vertical = self.enqueue("vertical", params={**PARAMS, "direction": "vertical-rl"})
        self.assertEqual(vertical["job_id"], "legacy")
        horizontal = self.enqueue("horizontal", params={**PARAMS, "direction": "horizontal-lr"})
        self.assertEqual(horizontal["job_id"], "horizontal")
        self.assertEqual(self.enqueue("default")["job_id"], "legacy")

    def test_simultaneous_submissions_across_database_instances_merge(self):
        databases = [Database(self.db_url) for _ in range(8)]
        barrier = threading.Barrier(len(databases))

        def submit(index):
            barrier.wait(timeout=10)
            return databases[index].enqueue_render(
                f"concurrent-{index}", "session-a", "永", "kai", PARAMS,
            )

        with ThreadPoolExecutor(max_workers=len(databases)) as pool:
            jobs = list(pool.map(submit, range(len(databases))))
        self.assertEqual(len({job["job_id"] for job in jobs}), 1)
        self.assertEqual(len(self.db.list_jobs("session-a")), 1)

    def test_simultaneous_claims_across_instances_have_one_winner(self):
        self.enqueue("first")
        databases = [Database(self.db_url) for _ in range(8)]
        barrier = threading.Barrier(len(databases))

        def claim(db):
            # Keep the first update open long enough for competing connections
            # to reproduce the former SELECT/UPDATE race deterministically.
            def delay_update(sql):
                if sql.startswith("UPDATE jobs SET status"):
                    time.sleep(0.05)
            db._get_sqlite_conn().set_trace_callback(delay_update)
            barrier.wait(timeout=10)
            return db.claim_next_job()

        with ThreadPoolExecutor(max_workers=len(databases)) as pool:
            claims = list(pool.map(claim, databases))
        winners = [job for job in claims if job is not None]
        self.assertEqual([job["job_id"] for job in winners], ["first"])
        self.assertEqual(winners[0]["status"], "rendering")

    def test_claim_is_render_only_and_fifo(self):
        self.db.create_job("preview", "session-a", "preview", "永", "kai", {})
        self.enqueue("first")
        self.enqueue("second", text="明")
        self.assertEqual(self.db.claim_next_job()["job_id"], "first")
        self.assertEqual(self.db.claim_next_job()["job_id"], "second")
        self.assertIsNone(self.db.claim_next_job())
        self.assertEqual(self.db.get_job("preview")["status"], "queued")


class RenderQueueApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_url = f"sqlite:///{Path(self.temp_dir.name) / 'api.db'}"
        self.db = Database(self.db_url)
        db_patch = patch("backend.app.get_db", return_value=self.db)
        db_patch.start()
        self.addCleanup(db_patch.stop)
        runner_patch = patch("backend.app.get_runner")
        self.runner = runner_patch.start().return_value
        self.addCleanup(runner_patch.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.client.cookies.set("calligraphy_session", "session-a")
        self.request = {"text": "永", "style": "kai"}

    def submit(self, request=None, client=None):
        response = (client or self.client).post("/api/renders", json=request or self.request)
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    def test_api_returns_existing_job_and_current_active_status(self):
        first = self.submit()
        self.assertEqual(first["status"], "queued")
        explicit_defaults = {**self.request, **PARAMS}
        self.assertEqual(self.submit(explicit_defaults)["job_id"], first["job_id"])
        for status in ("rendering", "running"):
            self.db.update_job(first["job_id"], status=status)
            duplicate = self.submit()
            self.assertEqual(duplicate["job_id"], first["job_id"])
            self.assertEqual(duplicate["status"], status)
        self.assertEqual(len(self.client.get("/api/jobs").json()["jobs"]), 1)
        self.assertTrue(self.runner.notify.called)

    def test_api_resolves_style_alias_before_deduplication(self):
        first = self.submit({**self.request, "style": "longcang-xingshu"})
        duplicate = self.submit({**self.request, "style": "longcang"})
        self.assertEqual(first["job_id"], duplicate["job_id"])

    def test_api_other_users_are_separate_and_cannot_access_job(self):
        first = self.submit()
        with TestClient(app) as other_client:
            other_client.cookies.set("calligraphy_session", "session-b")
            other = self.submit(client=other_client)
            self.assertNotEqual(first["job_id"], other["job_id"])
            self.assertEqual(other_client.get(f"/api/jobs/{first['job_id']}").status_code, 404)
            self.assertEqual([job["job_id"] for job in other_client.get("/api/jobs").json()["jobs"]], [other["job_id"]])

    def test_api_failed_and_completed_requests_create_new_jobs(self):
        first = self.submit()
        self.db.update_job(first["job_id"], status="failed", completed=True)
        retry = self.submit()
        self.assertNotEqual(first["job_id"], retry["job_id"])
        self.db.update_job(retry["job_id"], status="succeeded", completed=True)
        again = self.submit()
        self.assertNotIn(again["job_id"], (first["job_id"], retry["job_id"]))

    def test_api_render_parameters_do_not_merge(self):
        first = self.submit()
        for name, value in (("fps", 30), ("speed", 2.0), ("spacing", 0.4), ("text", "明"), ("style", "yan")):
            with self.subTest(parameter=name):
                # These are separate editing sessions, rather than a rate-limit test.
                self.client.cookies.set("calligraphy_session", f"parameters-{name}")
                other = self.submit({**self.request, name: value})
                self.assertNotEqual(first["job_id"], other["job_id"])

    def test_simultaneous_api_requests_merge_for_existing_session(self):
        barrier = threading.Barrier(6)

        def submit(_):
            client = TestClient(app)
            client.cookies.set("calligraphy_session", "session-a")
            try:
                barrier.wait(timeout=10)
                return self.submit(client=client)
            finally:
                client.close()

        # Separate Database objects for middleware and endpoints mirror multiple
        # API instances sharing the same SQLite file.
        with patch("backend.app.get_db", side_effect=lambda: Database(self.db_url)):
            with ThreadPoolExecutor(max_workers=6) as pool:
                jobs = list(pool.map(submit, range(6)))
        self.assertEqual(len({job["job_id"] for job in jobs}), 1)
        self.assertEqual(len(self.db.list_jobs("session-a")), 1)

    def test_synchronous_preview_is_never_available_to_background_worker(self):
        worker_db = Database(self.db_url)
        output = Path(self.temp_dir.name) / "preview.svg"
        output.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')

        def execute_preview(job, db):
            self.assertEqual(job["job_type"], "preview")
            self.assertEqual(job["status"], "rendering")
            self.assertIsNone(worker_db.claim_next_job())
            db.update_job(job["job_id"], status="succeeded", output_path=str(output), completed=True)
            return True

        with patch("backend.app.execute_job", side_effect=execute_preview) as execute:
            response = self.client.post("/api/previews", json=self.request)
        self.assertEqual(response.status_code, 200, response.text)
        execute.assert_called_once()
        self.assertIsNone(worker_db.claim_next_job())


if __name__ == "__main__":
    unittest.main()
