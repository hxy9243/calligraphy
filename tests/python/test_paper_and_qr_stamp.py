import unittest
import cv2
import numpy as np

from backend.retention import DEFAULT_RETENTION_SECONDS, PERMANENT_SHARE_TTL_SECONDS, job_share_token, job_share_url
from calligraphy.paper import (
    DEFAULT_STAMP_URL,
    compute_paper_grid,
    compute_stamp_placement,
    encode_qr_matrix,
    render_qr_seal_stamp,
    render_writing_paper,
)
from calligraphy.renderer import create_scene
from calligraphy.spec import Appearance, SceneSpec
from calligraphy.text.layout import layout_text


class PaperAndQrStampTests(unittest.TestCase):
    def test_qr_matrix_structure_and_finder_patterns(self):
        matrix = encode_qr_matrix(DEFAULT_STAMP_URL, ecc="M")
        self.assertEqual(matrix.shape, (33, 33))
        self.assertEqual(matrix.dtype, np.bool_)
        for r, c in ((0, 0), (0, 26), (26, 0)):
            finder = matrix[r : r + 7, c : c + 7]
            self.assertTrue(np.all(finder[0, :]))
            self.assertTrue(np.all(finder[6, :]))
            self.assertTrue(np.all(finder[:, 0]))
            self.assertTrue(np.all(finder[:, 6]))
            self.assertTrue(np.all(finder[2:5, 2:5]))

    def test_qr_seal_stamp_is_scannable_including_share_link_urls(self):
        detector = cv2.QRCodeDetector()
        paper_rgb = (246, 240, 228)
        share_url = job_share_url("vid_a1b2c3d4e5f6")
        test_cases = [
            (DEFAULT_STAMP_URL, 84),
            (DEFAULT_STAMP_URL, 96),
            (DEFAULT_STAMP_URL, 128),
            (share_url, 92),
            (share_url, 128),
        ]
        for url, size_px in test_cases:
            stamp = render_qr_seal_stamp(url, size_px=size_px, paper_rgb=paper_rgb)
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
            self.assertEqual(decoded, url, f"Failed to decode QR stamp at {size_px}px for {url}")

            ink_mask = arr[:, :, 3] > 120
            self.assertGreater(int(ink_mask.sum()), size_px * size_px // 8)
            red_vals = arr[:, :, 0][ink_mask]
            green_vals = arr[:, :, 1][ink_mask]
            self.assertGreater(float(red_vals.mean()), 155.0)
            self.assertLess(float(green_vals.mean()), 65.0)

            border_band = arr[2 : max(4, size_px // 14), size_px // 5 : 4 * size_px // 5, 3]
            has_ink = (border_band > 100).any(axis=0)
            self.assertTrue(has_ink.any())
            self.assertTrue((~has_ink).any(), "Outer border should contain weathered breaks")

    def test_evenly_distributed_ruling_lines_across_entire_page(self):
        # Even when there are only 2 columns of text, the paper should have evenly distributed lines across the whole page.
        grid = compute_paper_grid(720, 960, direction="vertical-rl", col_centers=(310.0, 410.0), cell_size=68.0)
        self.assertGreaterEqual(grid["n_lanes"], 5)
        centers = grid["lane_centers"]
        self.assertEqual(len(centers), grid["n_lanes"])
        diffs = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
        for d in diffs:
            self.assertAlmostEqual(d, grid["lane_width"], places=1)

    def test_all_paper_backgrounds_render_distinct_textures_and_preserve_corner_pixel(self):
        for style in ("xuan", "wusi", "gold", "unruled", "plain"):
            appearance = Appearance(paper_style=style, stamp_enabled=False)
            paper = np.asarray(render_writing_paper(480, 640, appearance=appearance))
            self.assertEqual(paper.shape, (640, 480, 3))
            self.assertEqual(tuple(int(v) for v in paper[0, 0]), appearance.paper_color)

    def test_stamp_positions_align_to_paper_lines_and_scan_cleanly(self):
        detector = cv2.QRCodeDetector()
        for pos in ("after-text", "next-line", "before-text", "corner", "custom"):
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
                    "appearance": {
                        "paper_style": "xuan",
                        "stamp_enabled": True,
                        "stamp_position": pos,
                        "stamp_col": 0 if pos == "custom" else None,
                        "stamp_row": 0.85 if pos == "custom" else None,
                    },
                }
            )
            scene = create_scene(spec)
            frame = np.asarray(scene.frame(scene.duration))
            self.assertEqual(tuple(int(v) for v in frame[0, 0]), spec.appearance.paper_color)
            schedule = scene.plan["schedule"]
            col_centers = tuple(sorted({round(float(e["x"]) + float(e["size"]) * 0.5, 1) for e in schedule}))
            row_centers = tuple(sorted({round(float(e["y"]) + float(e["size"]) * 0.5, 1) for e in schedule}))
            cell_size = round(float(schedule[0]["size"]), 2)
            grid = compute_paper_grid(720, 900, "vertical-rl", col_centers, row_centers, cell_size, 0.18)
            sx, sy, stamp_sz = compute_stamp_placement(
                720,
                900,
                "vertical-rl",
                grid,
                schedule,
                stamp_position=pos,
                stamp_col=spec.appearance.stamp_col,
                stamp_row=spec.appearance.stamp_row,
            )
            self.assertLess(stamp_sz, grid["lane_width"], f"Stamp size {stamp_sz} exceeds lane width {grid['lane_width']}")
            self.assertLessEqual(stamp_sz, 92, f"Stamp size {stamp_sz} is not small/delicate")
            y0 = max(0, sy - 20)
            y1 = min(900, sy + stamp_sz + 20)
            x0 = max(0, sx - 20)
            x1 = min(720, sx + stamp_sz + 20)
            crop_bgr = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_RGB2BGR)
            decoded, _, _ = detector.detectAndDecode(crop_bgr)
            self.assertEqual(decoded, DEFAULT_STAMP_URL, f"Stamp failed to decode in mode {pos}")

    def test_zigzag_layout_staggers_line_starts_within_margins(self):
        lines = ["永永永永", "永永永永", "永永永永", "永永永永"]
        rigid = layout_text(lines, direction="vertical-rl", width=720, height=960, zigzag=False)
        staggered = layout_text(lines, direction="vertical-rl", width=720, height=960, zigzag=True)
        rigid_first_y = [p["y"] for p in rigid["placements"] if p["row"] == 0]
        staggered_first_y = [p["y"] for p in staggered["placements"] if p["row"] == 0]
        # Rigid layout starts every column at the exact same Y
        self.assertEqual(len(set(round(y, 2) for y in rigid_first_y)), 1)
        # Zigzag layout staggers column start Y positions while staying within margins
        self.assertGreater(len(set(round(y, 2) for y in staggered_first_y)), 1)
        for p in staggered["placements"]:
            x0, y0 = p["x"], p["y"]
            x1, y1 = x0 + p["size"], y0 + p["size"]
            self.assertGreaterEqual(x0, 0.0)
            self.assertGreaterEqual(y0, 0.0)
            self.assertLessEqual(x1, 720.0)
            self.assertLessEqual(y1, 960.0)

    def test_retention_constants_and_deterministic_share_url(self):
        self.assertEqual(DEFAULT_RETENTION_SECONDS, 30 * 24 * 3600)
        self.assertGreaterEqual(PERMANENT_SHARE_TTL_SECONDS, 5 * 365 * 24 * 3600)
        tok = job_share_token("vid_test123")
        self.assertEqual(len(tok), 43)
        self.assertTrue(job_share_url("vid_test123").endswith(f"/watch.html#vid_test123.{tok}"))

    def test_video_stamp_timing_deferred_until_writing_ends_and_five_second_outro(self):
        from backend.composition import scene_spec_from_params
        detector = cv2.QRCodeDetector()
        spec = scene_spec_from_params(
            "永",
            "kai",
            {"width": 720, "height": 960, "paper_style": "xuan", "stamp_enabled": True, "stamp_position": "after-text"},
        )
        scene = create_scene(spec)
        schedule = scene.plan["schedule"]
        writing_end = schedule[-1]["end"]
        # Default outro is ~5.0s for reading pause after writing completes
        self.assertAlmostEqual(scene.duration - writing_end, 5.0, places=2)

        # 1. During writing (mid-stroke), stamp must NOT be present
        mid_frame = np.asarray(scene.frame(writing_end * 0.5))
        # Compute stamp bounding box
        schedule = scene.plan["schedule"]
        col_centers = tuple(sorted({round(float(e["x"]) + float(e["size"]) * 0.5, 1) for e in schedule}))
        row_centers = tuple(sorted({round(float(e["y"]) + float(e["size"]) * 0.5, 1) for e in schedule}))
        cell_size = round(float(schedule[0]["size"]), 2)
        grid = compute_paper_grid(720, 960, "vertical-rl", col_centers, row_centers, cell_size, 0.18)
        sx, sy, stamp_sz = compute_stamp_placement(720, 960, "vertical-rl", grid, schedule, stamp_position="after-text")
        pad = 20
        crop_mid = cv2.cvtColor(mid_frame[max(0, sy-pad):min(960, sy+stamp_sz+pad), max(0, sx-pad):min(720, sx+stamp_sz+pad)], cv2.COLOR_RGB2BGR)
        decoded_mid, _, _ = detector.detectAndDecode(crop_mid)
        self.assertEqual(decoded_mid, "", "Stamp should NOT be present on paper while writing is in progress")

        # 2. After writing completes during the outro pause, stamp is stamped and scannable
        end_frame = np.asarray(scene.frame(scene.duration))
        crop_end = cv2.cvtColor(end_frame[max(0, sy-pad):min(960, sy+stamp_sz+pad), max(0, sx-pad):min(720, sx+stamp_sz+pad)], cv2.COLOR_RGB2BGR)
        decoded_end, _, _ = detector.detectAndDecode(crop_end)
        self.assertEqual(decoded_end, DEFAULT_STAMP_URL, "Stamp should be present and scannable at end of video")


if __name__ == "__main__":
    unittest.main()
