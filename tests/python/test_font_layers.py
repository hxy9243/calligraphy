import tempfile
from pathlib import Path
import unittest

import numpy as np

from calligraphy.font_pipeline import target_masks
from calligraphy.font_layers import (
    FontLayerScene,
    LayerStore,
    prepare_character_layers,
)
from calligraphy.spec import SceneSpec, RenderPlan, Transforms, Appearance
from tests.python.test_font_pipeline import make_font, CROSS


class FontLayersTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.font_path = Path(self.temp_dir.name) / "test.ttf"
        make_font(self.font_path)

        for char, target in target_masks(self.font_path, ["十"]):
            self.target = target
            self.layers, self.phases, self.error = prepare_character_layers(target, CROSS)

        self.store = LayerStore(cache_dir=Path(self.temp_dir.name) / "cache")
        self.store.put("十", self.target, self.layers, self.phases)

    def test_exact_reconstruction(self):
        # Shape guarantee: composite matches target mask exactly with 0 error
        self.assertEqual(self.error, 0.0)
        reconstructed = np.zeros_like(self.target)
        for layer in self.layers:
            reconstructed = np.maximum(reconstructed, layer)
        max_error = float(np.max(np.abs(reconstructed - self.target)))
        self.assertEqual(max_error, 0.0)

    def test_monotonic_ink_accumulation(self):
        spec = SceneSpec(
            text="十",
            timing={"intro": 0.0, "outro": 0.0, "stroke_seconds": 1.0},
        )
        plan = RenderPlan.create(spec, stroke_counts={"十": len(self.layers)})
        scene = FontLayerScene(plan, self.store)

        entry = plan.schedule[0]
        # Sample partial stroke progress at fine intervals
        times = np.linspace(0.0, plan.duration, 25)
        previous_mask = np.zeros((480, 480), dtype=np.float32)

        for t in times:
            mask = scene._partial_mask(entry, t)
            diff = mask - previous_mask
            self.assertGreaterEqual(
                float(np.min(diff)),
                -1e-5,
                f"Ink disappeared at time {t}",
            )
            previous_mask = mask

        # At completion, partial mask matches target mask
        final_mask = scene._partial_mask(entry, plan.duration)
        np.testing.assert_allclose(final_mask, self.target, atol=1e-5)

    def test_zero_outro_completion(self):
        spec = SceneSpec(
            text="十",
            timing={"intro": 0.0, "outro": 0.0, "stroke_seconds": 0.5},
        )
        plan = RenderPlan.create(spec, stroke_counts={"十": len(self.layers)})
        scene = FontLayerScene(plan, self.store)
        frame_at_end = scene.frame(plan.duration)
        self.assertEqual(frame_at_end.size, (plan.width, plan.height))

    def test_backward_seeking_and_shared_assets(self):
        spec = SceneSpec(
            text="十十",
            timing={"intro": 0.5, "outro": 1.0, "stroke_seconds": 0.5, "character_gap": 0.2},
        )
        plan = RenderPlan.create(spec, stroke_counts={"十": len(self.layers)})
        scene = FontLayerScene(plan, self.store)

        # Forward seek
        frame_mid = scene.frame(plan.duration / 2.0)
        frame_end = scene.frame(plan.duration)

        # Backward seek
        frame_back = scene.frame(plan.duration / 2.0)
        np.testing.assert_array_equal(
            np.asarray(frame_mid),
            np.asarray(frame_back),
            "Backward seek did not reproduce the same frame",
        )

        # Confirm repeated characters reuse cached LayerStore entry
        self.assertIsNotNone(self.store.get("十"))

    def test_transforms_and_appearance(self):
        transforms = Transforms(scale=1.1, stretch=0.95, rotation=3.0)
        appearance = Appearance(paper_color=(240, 235, 220), ink_color=(30, 20, 10))
        spec = SceneSpec(
            text="十",
            transforms=transforms,
            appearance=appearance,
        )
        plan = RenderPlan.create(spec, stroke_counts={"十": len(self.layers)})
        scene = FontLayerScene(plan, self.store, appearance=appearance, transforms=transforms)
        frame = scene.frame(plan.duration)
        self.assertEqual(frame.size, (plan.width, plan.height))
        # Verify paper color at top-left corner
        pixel = frame.getpixel((0, 0))
        self.assertEqual(pixel, (240, 235, 220))


if __name__ == "__main__":
    unittest.main()
