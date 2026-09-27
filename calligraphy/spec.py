"""Versioned SceneSpec and RenderPlan contracts for Calligraphy Studio."""
from dataclasses import dataclass, field, asdict
import hashlib
import json
import math
from typing import Dict, Any, List, Optional, Tuple

from .text.input import parse_text
from .text.plan import create_text_plan

RENDERER_VERSION = "calligraphy-engine-v1"


def _parse_color(color: Any, name: str) -> Tuple[int, int, int]:
    """Parse hex string or RGB tuple into (r, g, b)."""
    if isinstance(color, (list, tuple)) and len(color) == 3:
        if all(isinstance(c, int) and 0 <= c <= 255 for c in color):
            return tuple(color)
    if isinstance(color, str):
        c = color.strip().lstrip("#")
        if len(c) == 6:
            try:
                return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
            except ValueError:
                pass
    raise ValueError(f"{name} must be a valid hex color (#RRGGBB) or RGB tuple (r, g, b)")


@dataclass(frozen=True)
class Appearance:
    paper_color: Tuple[int, int, int] = (248, 243, 233)
    ink_color: Tuple[int, int, int] = (28, 27, 24)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Appearance":
        if not data:
            return cls()
        paper = _parse_color(data.get("paper_color", data.get("paper", "#f8f3e9")), "paper_color")
        ink = _parse_color(data.get("ink_color", data.get("ink", "#1c1b18")), "ink_color")
        return cls(paper_color=paper, ink_color=ink)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_color": list(self.paper_color),
            "ink_color": list(self.ink_color),
        }


@dataclass(frozen=True)
class Transforms:
    scale: float = 1.0        # Allowed: 0.8 - 1.2
    stretch: float = 1.0      # Allowed: 0.9 - 1.1 (horizontal stretch)
    rotation: float = 0.0     # Allowed: -5.0 - 5.0 (degrees)

    def __post_init__(self):
        if not (0.8 - 1e-6 <= self.scale <= 1.2 + 1e-6):
            raise ValueError(f"scale must be between 0.8 and 1.2, got {self.scale}")
        if not (0.9 - 1e-6 <= self.stretch <= 1.1 + 1e-6):
            raise ValueError(f"stretch must be between 0.9 and 1.1, got {self.stretch}")
        if not (-5.0 - 1e-6 <= self.rotation <= 5.0 + 1e-6):
            raise ValueError(f"rotation must be between -5.0 and 5.0 degrees, got {self.rotation}")

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "Transforms":
        if not data:
            return cls()
        return cls(
            scale=float(data.get("scale", 1.0)),
            stretch=float(data.get("stretch", 1.0)),
            rotation=float(data.get("rotation", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scale": self.scale,
            "stretch": self.stretch,
            "rotation": self.rotation,
        }


def check_placement_bounds(
    x: float, y: float, size: float, transforms: Transforms, page_width: int, page_height: int
) -> Tuple[float, float, float, float]:
    """Compute and validate transformed bounding box against page boundaries.
    
    Returns (min_x, min_y, max_x, max_y).
    """
    # Cell center
    cx = x + size / 2.0
    cy = y + size / 2.0
    # Half-extents under scale and stretch
    hw = (size * 0.92 / 2.0) * transforms.scale * transforms.stretch
    hh = (size * 0.92 / 2.0) * transforms.scale
    rad = math.radians(transforms.rotation)
    cos_a, sin_a = abs(math.cos(rad)), abs(math.sin(rad))
    # Bounding box of rotated rectangle
    bb_hw = hw * cos_a + hh * sin_a
    bb_hh = hw * sin_a + hh * cos_a

    min_x, max_x = cx - bb_hw, cx + bb_hw
    min_y, max_y = cy - bb_hh, cy + bb_hh

    if min_x < -1e-4 or min_y < -1e-4 or max_x > page_width + 1e-4 or max_y > page_height + 1e-4:
        raise ValueError(
            f"Transformed glyph bounds ({min_x:.1f}, {min_y:.1f}, {max_x:.1f}, {max_y:.1f}) exceed page boundaries ({page_width}x{page_height})"
        )
    return (min_x, min_y, max_x, max_y)


@dataclass
class SceneSpec:
    text: str
    style: str = "kai"
    layout: Dict[str, Any] = field(default_factory=dict)
    timing: Dict[str, Any] = field(default_factory=dict)
    punctuation: str = "break"
    appearance: Appearance = field(default_factory=Appearance)
    transforms: Transforms = field(default_factory=Transforms)
    schema_version: int = 1

    def __post_init__(self):
        parsed = parse_text(self.text, punctuation=self.punctuation)
        self.normalized_characters = parsed["characters"]
        self.unique_characters = parsed["uniqueCharacters"]
        self.omitted = parsed["omitted"]

    @property
    def spec_hash(self) -> str:
        d = self.to_dict()
        return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "text": self.text,
            "style": self.style,
            "layout": self.layout,
            "timing": self.timing,
            "punctuation": self.punctuation,
            "appearance": self.appearance.to_dict(),
            "transforms": self.transforms.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneSpec":
        return cls(
            text=data["text"],
            style=data.get("style", "kai"),
            layout=data.get("layout", {}),
            timing=data.get("timing", {}),
            punctuation=data.get("punctuation", "break"),
            appearance=Appearance.from_dict(data.get("appearance")),
            transforms=Transforms.from_dict(data.get("transforms")),
            schema_version=data.get("schemaVersion", 1),
        )


@dataclass
class RenderPlan:
    scene_spec: SceneSpec
    width: int
    height: int
    direction: str
    stroke_seconds: float
    duration: float
    schedule: List[Dict[str, Any]]
    omitted: List[str]
    glyph_hashes: Dict[str, str] = field(default_factory=dict)
    renderer_version: str = RENDERER_VERSION
    schema_version: int = 1

    @classmethod
    def create(
        cls,
        scene_spec: SceneSpec,
        stroke_counts: Dict[str, int],
        glyph_hashes: Optional[Dict[str, str]] = None,
    ) -> "RenderPlan":
        base_plan = create_text_plan(
            scene_spec.text,
            stroke_counts=stroke_counts,
            layout=scene_spec.layout,
            timing=scene_spec.timing,
            punctuation=scene_spec.punctuation,
        )

        schedule = []
        for entry in base_plan["schedule"]:
            bounds = check_placement_bounds(
                entry["x"],
                entry["y"],
                entry["size"],
                scene_spec.transforms,
                base_plan["width"],
                base_plan["height"],
            )
            schedule.append({**entry, "transformedBounds": list(bounds)})

        return cls(
            scene_spec=scene_spec,
            width=base_plan["width"],
            height=base_plan["height"],
            direction=base_plan["direction"],
            stroke_seconds=base_plan["strokeSeconds"],
            duration=base_plan["duration"],
            schedule=schedule,
            omitted=base_plan["omitted"],
            glyph_hashes=glyph_hashes or {},
            renderer_version=RENDERER_VERSION,
            schema_version=1,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "rendererVersion": self.renderer_version,
            "sceneSpec": self.scene_spec.to_dict(),
            "width": self.width,
            "height": self.height,
            "direction": self.direction,
            "strokeSeconds": self.stroke_seconds,
            "duration": self.duration,
            "schedule": self.schedule,
            "omitted": self.omitted,
            "glyphHashes": self.glyph_hashes,
        }
