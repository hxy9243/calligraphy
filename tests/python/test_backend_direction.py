"""Direction survives validation, durable job params and the shared scene plan."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Database
from backend.worker import execute_job
from calligraphy.spec import RenderPlan


class BackendDirectionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.output_dir = Path(self.temp_dir.name) / "outputs"
        self.db = Database(f"sqlite:///{Path(self.temp_dir.name) / 'jobs.db'}")
        self.specs = []
        self.scenes = []

        def create_test_scene(spec, **kwargs):
            self.specs.append(spec)
            # Exercise the actual shared geometry/layout plan, without expensive
            # glyph preparation or encoding. Both exporters receive this scene.
            scene = SimpleNamespace(
                plan=RenderPlan.create(spec, stroke_counts={"永": 1}),
                frame_svg=lambda time: "<svg/>",
            )
            self.scenes.append(scene)
            return scene

        def write_output(scene, output, **kwargs):
            Path(output).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")

        self.runner = Mock()
        self.start_patch("backend.app.get_db", return_value=self.db)
        self.start_patch("backend.app.get_runner", return_value=self.runner)
        self.start_patch("backend.worker._auto_prepare_font")
        self.start_patch("backend.worker.create_scene", side_effect=create_test_scene)
        self.start_patch("backend.worker.Path", side_effect=lambda value: self.output_dir if value == "outputs" else Path(value))
        self.export_svg = self.start_patch("backend.worker.export_svg", side_effect=write_output)
        self.export_still = self.start_patch("backend.worker.export_still", side_effect=write_output)
        self.export_video = self.start_patch("backend.worker.export_video", side_effect=write_output)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def start_patch(self, *args, **kwargs):
        patcher = patch(*args, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def assert_direction(self, direction):
        self.assertEqual(self.specs[-1].layout["direction"], direction)
        plan = self.scenes[-1].plan
        self.assertEqual(plan.direction, direction)
        first, second, third, _ = plan.schedule
        if direction == "horizontal-lr":
            self.assertGreater(second["x"], first["x"])
            self.assertEqual(second["y"], first["y"])
            self.assertEqual(third["x"], first["x"])
            self.assertGreater(third["y"], first["y"])
        else:
            self.assertEqual(second["x"], first["x"])
            self.assertGreater(second["y"], first["y"])
            self.assertLess(third["x"], first["x"])
            self.assertEqual(third["y"], first["y"])

    def test_preview_validates_persists_and_forwards_direction_for_svg_and_png(self):
        for direction in (None, "vertical-rl", "horizontal-lr"):
            for output_format, exporter in (("auto", self.export_svg), ("png", self.export_still)):
                with self.subTest(direction=direction, output_format=output_format):
                    payload = {"text": "永永\n永永", "format": output_format}
                    if direction is not None:
                        payload["direction"] = direction
                    response = self.client.post("/api/previews", json=payload)
                    self.assertEqual(response.status_code, 200, response.text)
                    job = self.db.get_job(response.json()["job_id"])
                    expected = direction or "vertical-rl"
                    self.assertEqual(job["params"]["direction"], expected)
                    self.assertEqual(job["status"], "succeeded")
                    self.assert_direction(expected)
                    self.assertIs(exporter.call_args.args[0], self.scenes[-1])

    def test_video_validates_persists_and_forwards_direction_to_export(self):
        for direction in (None, "vertical-rl", "horizontal-lr"):
            with self.subTest(direction=direction):
                payload = {"text": "永永\n永永", "fps": 12, "speed": 2}
                if direction is not None:
                    payload["direction"] = direction
                response = self.client.post("/api/renders", json=payload)
                self.assertEqual(response.status_code, 202, response.text)
                job = self.db.get_job(response.json()["job_id"])
                expected = direction or "vertical-rl"
                self.assertEqual(job["params"]["direction"], expected)
                self.assertTrue(execute_job(job, self.db))
                self.assert_direction(expected)
                self.assertIs(self.export_video.call_args.args[0], self.scenes[-1])
                self.assertEqual(self.export_video.call_args.kwargs, {"fps": 12, "speed": 2.0})

    def test_direction_changes_create_distinct_render_jobs(self):
        job_ids = []
        for direction in ("vertical-rl", "horizontal-lr"):
            response = self.client.post(
                "/api/renders", json={"text": "永永\n永永", "style": "kai", "direction": direction},
            )
            self.assertEqual(response.status_code, 202, response.text)
            job_id = response.json()["job_id"]
            job_ids.append(job_id)
            self.assertEqual(self.db.get_job(job_id)["params"]["direction"], direction)
        self.assertNotEqual(*job_ids)

    def test_unsupported_directions_rejected_without_creating_jobs(self):
        for endpoint in ("/api/previews", "/api/renders"):
            for direction in ("diagonal", "horizontal", "vertical-lr", "", None, 1):
                with self.subTest(endpoint=endpoint, direction=direction):
                    response = self.client.post(endpoint, json={"text": "永", "direction": direction})
                    self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get("/api/jobs").json()["jobs"], [])
        self.assertEqual(self.specs, [])
        self.runner.notify.assert_not_called()

    def test_existing_jobs_without_direction_still_default_to_vertical(self):
        job = self.db.create_job(
            job_id="old_video", session_id="test_session", job_type="render",
            text="永永\n永永", style="kai", params={},
        )
        self.assertTrue(execute_job(job, self.db))
        self.assert_direction("vertical-rl")

    def test_openapi_documents_the_two_modes_and_backwards_compatible_default(self):
        schemas = self.client.get("/openapi.json").json()["components"]["schemas"]
        for name in ("PreviewRequest", "RenderRequest"):
            direction = schemas[name]["properties"]["direction"]
            self.assertEqual(direction["enum"], ["vertical-rl", "horizontal-lr"])
            self.assertEqual(direction["default"], "vertical-rl")


if __name__ == "__main__":
    unittest.main()
