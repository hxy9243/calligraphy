"""Fast static preview rendering tests verifying engine bypass."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from backend.database import Database
from backend.worker import execute_job
from calligraphy.renderer import StaticFontScene, create_scene
from calligraphy.spec import SceneSpec, RenderPlan


class FastStaticPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = Database(f"sqlite:///{self.root / 'jobs.db'}")
        env = patch.dict(os.environ, {
            "CALLIGRAPHY_OUTPUT_DIR": str(self.root / "outputs"),
        })
        env.start()
        self.addCleanup(env.stop)

    def test_preview_job_bypasses_auto_prepare_font_for_catalog_fonts(self):
        # mashanzheng is a bundled font in data/fonts/
        job = self.db.create_job(
            "test_fast_static_1",
            "test_user",
            "preview",
            "永和九年",
            "mashanzheng",
            {"format": "auto", "stamp_enabled": True},
        )
        with patch("backend.worker._auto_prepare_font", side_effect=AssertionError("Must not call _auto_prepare_font for static preview")):
            success = execute_job(job, self.db)
        self.assertTrue(success)
        saved = self.db.get_job(job["job_id"])
        self.assertEqual(saved["status"], "succeeded")
        out_file = Path(saved["output_path"])
        self.assertTrue(out_file.exists())
        self.assertTrue(out_file.name.endswith(".svg"))
        content = out_file.read_text(encoding="utf-8")
        self.assertIn('data-engine="static-font"', content)
        self.assertIn('class="seal-stamp-vector"', content)
        self.assertIn('<image', content)

    def test_preview_job_png_format(self):
        job = self.db.create_job(
            "test_fast_static_2",
            "test_user",
            "preview",
            "永和九年",
            "mashanzheng",
            {"format": "png", "stamp_enabled": True, "width": 400, "height": 600},
        )
        with patch("backend.worker._auto_prepare_font", side_effect=AssertionError("Must not call _auto_prepare_font")):
            success = execute_job(job, self.db)
        self.assertTrue(success)
        saved = self.db.get_job(job["job_id"])
        self.assertEqual(saved["status"], "succeeded")
        out_file = Path(saved["output_path"])
        self.assertTrue(out_file.exists())
        self.assertTrue(out_file.name.endswith(".png"))
        with Image.open(out_file) as img:
            self.assertEqual(img.size, (400, 600))

    def test_static_font_scene_direct_usage(self):
        spec = SceneSpec(text="永和", style="mashanzheng")
        font_path = Path(__file__).resolve().parent.parent.parent / "data" / "fonts" / "MaShanZheng.ttf"
        plan = RenderPlan.create(spec, stroke_counts={"永": 1, "和": 1})
        scene = StaticFontScene(plan, font_path)
        self.assertEqual(scene.style, "mashanzheng")
        self.assertIsNone(scene.render_warning)
        img = scene.frame()
        self.assertIsInstance(img, Image.Image)
        img.close()
        svg = scene.frame_svg()
        self.assertIn("<svg", svg)
        self.assertIn('data-engine="static-font"', svg)


if __name__ == "__main__":
    unittest.main()
