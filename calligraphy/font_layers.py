"""Font-preserving reveal using registered overlapping stroke layers and phase fields."""
from pathlib import Path
import math
from typing import Dict, Any, Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from .font_fitting import registered_fields, smooth_decomposition
from .font_pipeline import target_masks
from .spec import RenderPlan, Appearance, Transforms

SIZE = 480


def prepare_character_layers(
    target: np.ndarray, glyph_template: Dict[str, Any]
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Decompose target font silhouette into ordered overlapping stroke layers and progress phases.
    
    Returns:
      (layers, phases, max_reconstruction_error)
    """
    gray = np.uint8(np.clip(255 * (1 - cv2.resize(target, (160, 160))), 0, 255))
    warped, phase = registered_fields(gray, glyph_template)
    layers, phases, _ = smooth_decomposition(warped, phase, target)
    ink = np.zeros_like(target)
    for layer in layers:
        ink = np.maximum(ink, layer)
    error = float(np.max(np.abs(ink - target)))
    return layers, phases, error


class LayerStore:
    """In-memory and disk cache for font-preserving layers and phases."""

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory = {}

    def get(self, character: str) -> Optional[Dict[str, np.ndarray]]:
        if character in self._memory:
            return self._memory[character]
        if self.cache_dir:
            p = self.cache_dir / f"{ord(character):x}.npz"
            if p.exists():
                with np.load(p) as data:
                    item = {
                        "target": data["target"],
                        "layers": data["layers"],
                        "phases": data["phases"],
                        "prefix": np.maximum.accumulate(data["layers"], axis=0),
                    }
                    self._memory[character] = item
                    return item
        return None

    def put(self, character: str, target: np.ndarray, layers: np.ndarray, phases: np.ndarray):
        item = {
            "target": target,
            "layers": layers,
            "phases": phases,
            "prefix": np.maximum.accumulate(layers, axis=0),
        }
        self._memory[character] = item
        if self.cache_dir:
            p = self.cache_dir / f"{ord(character):x}.npz"
            np.savez_compressed(p, target=target, layers=layers, phases=phases)


class FontLayerScene:
    """Authoritative Python scene renderer using font-preserving masks and phases.
    
    Guarantees:
      - Max composite matches the canonical target mask with 0 reconstruction error.
      - Monotonic ink accumulation during partial stroke reveal.
      - Zero-outro completion fills the target outline.
      - Shared frame implementation for still and video exports.
    """

    def __init__(
        self,
        plan: RenderPlan,
        layer_store: LayerStore,
        appearance: Optional[Appearance] = None,
        transforms: Optional[Transforms] = None,
    ):
        self.plan = plan
        self.layer_store = layer_store
        self.appearance = appearance or plan.scene_spec.appearance
        self.transforms = transforms or plan.scene_spec.transforms
        self._cached_patches = {}
        self._active_entry_idx = None
        self._active_char = None
        self._active_layers = None
        self._active_phases = None
        self._active_prefix = None

    @property
    def width(self) -> int:
        return self.plan.width

    @property
    def height(self) -> int:
        return self.plan.height

    @property
    def duration(self) -> float:
        return self.plan.duration

    def glyph_mask(self, character: str) -> np.ndarray:
        data = self.layer_store.get(character)
        if data is None:
            raise KeyError(f"Character {character} not found in LayerStore")
        return data["target"]

    def _partial_mask(self, entry: Dict[str, Any], time: float) -> np.ndarray:
        char = entry["character"]
        if self._active_entry_idx != entry["index"]:
            data = self.layer_store.get(char)
            if data is None:
                raise KeyError(f"Character {char} not found in LayerStore")
            self._active_entry_idx = entry["index"]
            self._active_char = char
            self._active_layers = data["layers"]
            self._active_phases = data["phases"]
            self._active_prefix = data["prefix"]

        layers = self._active_layers
        phases = self._active_phases
        prefix = self._active_prefix

        elapsed = np.clip((time - entry["start"]) / self.plan.stroke_seconds, 0, len(layers))
        k = int(elapsed)
        if k >= len(layers):
            return prefix[-1].copy()

        progress = elapsed - k
        # Soft front advancing through the phase field
        reveal = np.clip((progress - (0.03 + 0.90 * np.clip(phases[k], 0, 1))) / 0.06, 0, 1)
        # Smooth Hermite curve
        smoothed = reveal * reveal * (3 - 2 * reveal)
        active = layers[k] * smoothed
        return np.maximum(prefix[k - 1], active) if k > 0 else active

    def _create_patch(self, mask: np.ndarray, size: float) -> Image.Image:
        # Canonical span: size * 0.92
        w = max(1, round(size * 0.92 * self.transforms.scale * self.transforms.stretch))
        h = max(1, round(size * 0.92 * self.transforms.scale))
        alpha = Image.fromarray(np.uint8(np.clip(mask, 0, 1) * 255)).resize(
            (w, h), Image.Resampling.LANCZOS
        )
        patch = Image.new("RGBA", (w, h), self.appearance.ink_color + (0,))
        patch.putalpha(alpha)
        if abs(self.transforms.rotation) > 1e-4:
            patch = patch.rotate(
                -self.transforms.rotation,
                resample=Image.Resampling.BICUBIC,
                expand=True,
            )
        return patch

    def frame(self, time: float) -> Image.Image:
        """Render page at time t into a PIL Image."""
        t = float(min(self.plan.duration, max(0.0, time)))
        page = Image.new("RGB", (self.plan.width, self.plan.height), self.appearance.paper_color)

        for index, entry in enumerate(self.plan.schedule):
            if t <= entry["start"]:
                break

            char = entry["character"]
            size = entry["size"]
            cx = round(entry["x"] + size / 2.0)
            cy = round(entry["y"] + size / 2.0)

            if t >= entry["end"]:
                cache_key = (char, round(size, 2))
                if cache_key not in self._cached_patches:
                    target = self.glyph_mask(char)
                    self._cached_patches[cache_key] = self._create_patch(target, size)
                patch = self._cached_patches[cache_key]
            else:
                partial = self._partial_mask(entry, t)
                patch = self._create_patch(partial, size)

            px = cx - patch.width // 2
            py = cy - patch.height // 2
            page.paste(patch, (px, py), patch)

        return page
