import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from calligraphy.cli import main, parse_args
from calligraphy.spec import Transforms, check_placement_bounds


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name)

    def test_list_styles(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = main(["--list-styles"])
            self.assertEqual(exit_code, 0)
            output = mock_stdout.getvalue()
            self.assertIn("kai: template", output)
            self.assertIn("yan: template", output)
            self.assertIn("lishu: contact brush", output)

    def test_text_and_text_file_exclusivity(self):
        # Neither provided
        self.assertEqual(main(["--output", str(self.work_dir / "out.png")]), 1)
        # Both provided
        dummy_file = self.work_dir / "dummy.txt"
        dummy_file.write_text("明月", encoding="utf-8")
        self.assertEqual(
            main(["--text", "明月", "--text-file", str(dummy_file), "--output", str(self.work_dir / "out.png")]),
            1,
        )

    def test_render_png_and_svg_kai(self):
        png_out = self.work_dir / "test.png"
        exit_code = main(["--text", "明月", "--style", "kai", "--output", str(png_out), "--width", "128", "--height", "128"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(png_out.exists())
        with Image.open(png_out) as img:
            self.assertEqual(img.size, (128, 128))

        svg_out = self.work_dir / "test.svg"
        exit_code = main(["--text", "明月", "--style", "yan", "--output", str(svg_out), "--width", "128", "--height", "128"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(svg_out.exists())
        svg_content = svg_out.read_text(encoding="utf-8")
        self.assertIn("<svg", svg_content)
        self.assertIn('data-character="明"', svg_content)

    def test_render_mp4_smoke(self):
        mp4_out = self.work_dir / "test.mp4"
        exit_code = main([
            "--text", "永",
            "--style", "kai",
            "--output", str(mp4_out),
            "--width", "128",
            "--height", "128",
            "--fps", "4",
            "--intro", "0",
            "--outro", "0",
            "--stroke-seconds", "0.25",
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(mp4_out.exists())
        self.assertGreater(mp4_out.stat().st_size, 1000)

    def test_render_mp4_parallel_workers(self):
        mp4_out = self.work_dir / "test_workers.mp4"
        exit_code = main([
            "--text", "永",
            "--style", "kai",
            "--output", str(mp4_out),
            "--width", "128",
            "--height", "128",
            "--fps", "4",
            "--intro", "0",
            "--outro", "0",
            "--stroke-seconds", "0.25",
            "--workers", "8",
        ])
        self.assertEqual(exit_code, 0)
        self.assertTrue(mp4_out.exists())
        self.assertGreater(mp4_out.stat().st_size, 1000)

    def test_transform_bounds_validation(self):
        with self.assertRaises(ValueError):
            Transforms(scale=1.5)  # > 1.2
        with self.assertRaises(ValueError):
            Transforms(stretch=0.7)  # < 0.9
        with self.assertRaises(ValueError):
            Transforms(rotation=15.0)  # > 5.0

        # Transformed bounds exceeding page bounds
        t = Transforms(scale=1.2, stretch=1.1, rotation=5.0)
        with self.assertRaises(ValueError):
            check_placement_bounds(x=0.0, y=0.0, size=200.0, transforms=t, page_width=100, page_height=100)


if __name__ == "__main__":
    unittest.main()
