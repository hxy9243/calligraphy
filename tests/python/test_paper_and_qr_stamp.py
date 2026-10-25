import unittest
import cv2
import numpy as np

from calligraphy.paper import (
    DEFAULT_STAMP_URL,
    encode_qr_matrix,
    render_qr_seal_stamp,
    render_writing_paper,
)
from calligraphy.renderer import create_scene
from calligraphy.spec import Appearance, SceneSpec


class PaperAndQrStampTests(unittest.TestCase):
    def test_qr_matrix_structure_and_finder_patterns(self):
        matrix = encode_qr_matrix(DEFAULT_STAMP_URL, ecc="M")
        self.assertEqual(matrix.shape, (33, 33))
        self.assertEqual(matrix.dtype, np.bool_)
        # Verify 7x7 finder pattern corners
        for r, c in ((0, 0), (0, 26), (26, 0)):
            finder = matrix[r : r + 7, c : c + 7]
            self.assertTrue(np.all(finder[0, :]))
            self.assertTrue(np.all(finder[6, :]))
            self.assertTrue(np.all(finder[:, 0]))
            self.assertTrue(np.all(finder[:, 6]))
            self.assertTrue(np.all(finder[2:5, 2:5]))

    def test_qr_seal_stamp_is_scannable_and_has_weathered_red_ink_and_border_breaks(self):
        detector = cv2.QRCodeDetector()
        paper_rgb = (246, 240, 228)
        for size_px in (96, 128, 160):
            stamp = render_qr_seal_stamp(DEFAULT_STAMP_URL, size_px=size_px, paper_rgb=paper_rgb)
            self.assertEqual(stamp.size, (size_px, size_px))
            self.assertEqual(stamp.mode, "RGBA")

            composite = np.full((size_px + 48, size_px + 48, 3), paper_rgb, dtype=np.uint8)
            arr = np.asarray(stamp, dtype=np.float32)
            alpha = arr[:, :, 3:4] / 255.0
            roi = composite[24 : 24 + size_px, 24 : 24 + size_px].astype(np.float32)
            composite[24 : 24 + size_px, 24 : 24 + size_px] = np.clip(
                roi * (1.0 - alpha) + arr[:, :, :3] * alpha, 0, 255
            ).astype(np.uint8)

            decoded, _, _ = detector.detectAndDecode(cv2.cvtColor(composite, cv2.COLOR_RGB2BGR))
            self.assertEqual(decoded, DEFAULT_STAMP_URL, f"Failed to decode QR stamp at {size_px}px")

            # Verify red-ink cinnabar characteristics (high R, much lower G/B) and variation
            ink_mask = arr[:, :, 3] > 120
            self.assertGreater(int(ink_mask.sum()), size_px * size_px // 8)
            red_vals = arr[:, :, 0][ink_mask]
            green_vals = arr[:, :, 1][ink_mask]
            self.assertGreater(float(red_vals.mean()), 155.0)
            self.assertLess(float(green_vals.mean()), 65.0)
            self.assertGreater(float(red_vals.std()), 3.5)

            # Verify outer border has weathered breaks (not a solid unbroken rectangle)
            # Sample along the outer border band
            border_band = arr[2 : max(4, size_px // 14), size_px // 5 : 4 * size_px // 5, 3]
            has_ink = (border_band > 100).any(axis=0)
            self.assertTrue(has_ink.any())
            self.assertTrue((~has_ink).any(), "Outer border should contain weathered breaks")

    def test_writing_paper_renders_ruling_and_scannable_corner_stamp(self):
        spec = SceneSpec.from_dict(
            {
                "version": 1,
                "text": "永\n永",
                "style": "kai",
                "layout": {
                    "direction": "vertical-rl",
                    "columns": 2,
                    "rows": 2,
                    "width": 720,
                    "height": 900,
                    "margin": 64,
                },
            }
        )
        scene = create_scene(spec)
        frame = np.asarray(scene.frame(scene.duration))
        self.assertEqual(frame.shape, (900, 720, 3))
        # Top-left pixel preserves paper_color invariant
        self.assertEqual(tuple(int(v) for v in frame[0, 0]), spec.appearance.paper_color)

        # Decode the corner QR stamp directly from the rendered calligraphy page
        detector = cv2.QRCodeDetector()
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # Check bottom-left corner crop where vertical-rl places the seal
        corner = bgr[frame.shape[0] // 2 :, : frame.shape[1] // 2]
        decoded, _, _ = detector.detectAndDecode(corner)
        self.assertEqual(decoded, DEFAULT_STAMP_URL)

    def test_plain_paper_style_disables_ruling_and_stamp(self):
        appearance = Appearance(paper_style="plain", stamp_url="")
        paper = np.asarray(render_writing_paper(320, 240, appearance=appearance))
        expected = np.full((240, 320, 3), appearance.paper_color, dtype=np.uint8)
        np.testing.assert_array_equal(paper, expected)


if __name__ == "__main__":
    unittest.main()
