"""Unified scene composition and multi-format export for Calligraphy Studio."""
import io
import math
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Union

import cairosvg
import numpy as np
from PIL import Image

from .animation import trace_polyline
from .contact_renderer import ContactScene, style_manifest, load_style
from .font_layers import FontLayerScene, LayerStore, prepare_character_layers
from .font_pipeline import style_path, load_bank, target_masks
from .spec import SceneSpec, RenderPlan, Appearance, Transforms
from .text.glyphs import resolve_glyphs, load_bundled_glyphs
from .text.plan import create_text_plan

TEMPLATE_EXPANSIONS = {
    "kai": 0.0,
    "yan": 16.48,
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class TemplateScene:
    """Deterministic vector template scene (Kai, Yan) with SVG and raster outputs."""

    def __init__(
        self,
        plan: RenderPlan,
        glyph_records: Dict[str, Any],
        style: str = "kai",
    ):
        self.plan = plan
        self.glyph_records = glyph_records
        self.style = style
        self.expansion = TEMPLATE_EXPANSIONS.get(style, 0.0)
        self.appearance = plan.scene_spec.appearance
        self.transforms = plan.scene_spec.transforms

    @property
    def width(self) -> int:
        return self.plan.width

    @property
    def height(self) -> int:
        return self.plan.height

    @property
    def duration(self) -> float:
        return self.plan.duration

    def frame_svg(self, time: float) -> str:
        t = _clamp(float(time), 0.0, self.duration)
        paper_hex = f"#{self.appearance.paper_color[0]:02x}{self.appearance.paper_color[1]:02x}{self.appearance.paper_color[2]:02x}"
        ink_hex = f"#{self.appearance.ink_color[0]:02x}{self.appearance.ink_color[1]:02x}{self.appearance.ink_color[2]:02x}"

        marks = []
        for entry in self.plan.schedule:
            if t <= entry["start"]:
                continue
            char = entry["character"]
            data = self.glyph_records[char]
            strokes_svg = []
            for i, (path, median) in enumerate(zip(data["strokes"], data["medians"])):
                if t >= entry["end"]:
                    progress = 1.0
                else:
                    progress = _clamp((t - entry["start"] - i * self.plan.stroke_seconds) / self.plan.stroke_seconds)

                if progress <= 0:
                    continue
                if progress >= 1.0:
                    strokes_svg.append(
                        f'<path d="{path}" fill="{ink_hex}" stroke="{ink_hex}" '
                        f'stroke-width="{self.expansion}" stroke-linejoin="round"/>'
                    )
                else:
                    mask_id = f"text-{entry['index']}-{i}"
                    trace_path, _ = trace_polyline(median, progress)
                    strokes_svg.append(
                        f'<defs><mask id="{mask_id}" maskUnits="userSpaceOnUse" x="-64" y="-160" width="1152" height="1280">'
                        f'<path d="{path}" fill="white" stroke="white" stroke-width="{self.expansion}" stroke-linejoin="round"/>'
                        f'</mask></defs>'
                        f'<path d="{trace_path}" mask="url(#{mask_id})" fill="none" stroke="{ink_hex}" '
                        f'stroke-width="{174 + self.expansion}" stroke-linecap="round" stroke-linejoin="round"/>'
                    )

            strokes_content = "".join(strokes_svg)
            # Center of the cell
            cx = entry["x"] + entry["size"] / 2.0
            cy = entry["y"] + entry["size"] / 2.0
            scale_x = (entry["size"] * 0.92 / 1024.0) * self.transforms.scale * self.transforms.stretch
            scale_y = (entry["size"] * 0.92 / 1024.0) * self.transforms.scale
            rot = self.transforms.rotation

            transform = (
                f'translate({cx} {cy}) '
                f'rotate({rot}) '
                f'scale({scale_x} {scale_y}) '
                f'translate(-512 388) '
                f'scale(1 -1)'
            )
            marks.append(
                f'<g data-character="{char}" transform="{transform}">{strokes_content}</g>'
            )

        inner = "".join(marks)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">'
            f'<rect width="100%" height="100%" fill="{paper_hex}"/>{inner}</svg>'
        )

    def frame(self, time: float) -> Image.Image:
        svg = self.frame_svg(time)
        png_bytes = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=self.width, output_height=self.height)
        return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def export_svg(scene: Any, output: Union[str, Path], time: Optional[float] = None) -> None:
    if not hasattr(scene, "frame_svg"):
        raise ValueError(f"Scene {scene} does not support SVG export")
    dur = scene.duration if hasattr(scene, "duration") else scene.plan["duration"]
    t = dur if time is None else _clamp(float(time), 0.0, dur)
    p = Path(output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(scene.frame_svg(t), encoding="utf-8")


def export_png(scene: Any, output: Union[str, Path], time: Optional[float] = None) -> None:
    dur = scene.duration if hasattr(scene, "duration") else (scene.plan.duration if hasattr(scene.plan, "duration") else scene.plan["duration"])
    t = dur if time is None else _clamp(float(time), 0.0, dur)
    p = Path(output)
    p.parent.mkdir(parents=True, exist_ok=True)
    scene.frame(t).save(p, format="PNG")


def export_video(
    scene: Any,
    output: Union[str, Path],
    fps: int = 24,
    speed: float = 1.0,
    ffmpeg: str = "ffmpeg",
) -> int:
    if not isinstance(fps, int) or not (1 <= fps <= 240):
        raise ValueError(f"fps must be an integer between 1 and 240, got {fps}")
    if not (0.000001 <= speed <= 10.0):
        raise ValueError(f"speed must be between 0.000001 and 10, got {speed}")

    width = scene.width if hasattr(scene, "width") else (scene.plan.width if hasattr(scene.plan, "width") else scene.plan["width"])
    height = scene.height if hasattr(scene, "height") else (scene.plan.height if hasattr(scene.plan, "height") else scene.plan["height"])
    dur = scene.duration if hasattr(scene, "duration") else (scene.plan.duration if hasattr(scene.plan, "duration") else scene.plan["duration"])

    if width % 2 != 0 or height % 2 != 0:
        raise ValueError("Video width and height must be even integers")

    p = Path(output)
    p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        f"{width}x{height}",
        "-framerate",
        str(fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(p),
    ]

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    count = math.ceil(dur * fps / speed)
    try:
        for i in range(count):
            t = dur if i == count - 1 else (i / fps * speed)
            frame_img = scene.frame(t)
            process.stdin.write(frame_img.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("ffmpeg encoding failed")
    except BaseException:
        try:
            process.stdin.close()
        except OSError:
            pass
        if process.poll() is None:
            process.kill()
        process.wait()
        raise
    return count


def export_still(scene: Any, output: Union[str, Path], time: Optional[float] = None) -> None:
    p = Path(output)
    ext = p.suffix.lower()
    if ext == ".svg":
        export_svg(scene, p, time)
    elif ext == ".png":
        export_png(scene, p, time)
    else:
        raise ValueError(f"Still output must end in .png or .svg, got {ext}")


def create_scene(
    scene_spec: SceneSpec,
    font_path: Optional[Union[str, Path]] = None,
    glyphs: Optional[Dict[str, Any]] = None,
    fetch_missing: bool = False,
    mode: str = "auto",
) -> Any:
    """Create a renderable scene from a SceneSpec.
    
    Modes:
      - 'auto': chooses appropriate scene based on style.
      - 'template': vector TemplateScene (kai, yan).
      - 'contact': ContactScene for contact styles or registered font banks.
      - 'font_layers': FontLayerScene for exact font silhouette reconstruction.
    """
    style = scene_spec.style
    manifest = style_manifest()

    if style in TEMPLATE_EXPANSIONS:
        loaded_glyphs = resolve_glyphs(
            scene_spec.text,
            glyphs=glyphs,
            fetch_missing=fetch_missing,
            punctuation=scene_spec.punctuation,
        )
        stroke_counts = {c: len(loaded_glyphs[c]["strokes"]) for c in loaded_glyphs}
        plan = RenderPlan.create(scene_spec, stroke_counts=stroke_counts)
        return TemplateScene(plan, loaded_glyphs, style=style)

    if style in manifest["styles"]:
        contact_glyphs = load_style(style)
        stroke_counts = {c: len(contact_glyphs[c]) for c in contact_glyphs}
        plan = RenderPlan.create(scene_spec, stroke_counts=stroke_counts)
        # Convert plan to dict for ContactScene compatibility
        return ContactScene(plan.to_dict(), contact_glyphs)

    # Registered font bank
    bank = load_bank(style)
    font_file = font_path or bank["font"]["path"]
    missing = [c for c in scene_spec.normalized_characters if c not in bank["glyphs"]]
    if missing:
        raise ValueError(
            f"Missing prepared {style} glyphs: {' '.join(missing)}. "
            f"Prepare missing characters before rendering."
        )

    stroke_counts = {c: len(bank["glyphs"][c]) for c in bank["glyphs"]}
    plan = RenderPlan.create(scene_spec, stroke_counts=stroke_counts)

    if mode == "contact":
        return ContactScene(plan.to_dict(), bank["glyphs"])

    # Default to FontLayerScene for exact source font reconstruction
    store = LayerStore()
    for char, target in target_masks(font_file, scene_spec.unique_characters):
        cached = store.get(char)
        if cached is None:
            template = bank["templates"][char]
            layers, phases, error = prepare_character_layers(target, template)
            store.put(char, target, layers, phases)

    return FontLayerScene(plan, store, appearance=scene_spec.appearance, transforms=scene_spec.transforms)
