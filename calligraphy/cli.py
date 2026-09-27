"""Command line interface for Calligraphy Studio rendering."""
import argparse
import json
from pathlib import Path
import sys
from typing import Optional

from .contact_renderer import style_manifest
from .font_pipeline import registered_styles
from .renderer import create_scene, export_still, export_video
from .spec import SceneSpec, Appearance, Transforms
from .text.glyphs import bundled_glyphs


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Chinese calligraphy text into PNG, SVG, or MP4.",
        prog="calligraphy",
    )
    parser.add_argument("--list-styles", action="store_true", help="List built-in and locally registered styles")
    parser.add_argument("--text", type=str, help="Text to render")
    parser.add_argument("--text-file", type=str, help="File containing text to render")
    parser.add_argument("--glyphs", type=str, help="Path to JSON file with additional glyph definitions")
    parser.add_argument("--fetch", action="store_true", help="Fetch missing character records from Hanzi Writer Data")
    parser.add_argument("--output", "-o", type=str, default="outputs/text.png", help="Output file (.png, .svg, .mp4)")
    parser.add_argument("--style", type=str, default="kai", help="Style name (kai, yan, lishu, liu, yan-contact, etc.)")
    parser.add_argument("--width", type=int, default=1080, help="Page width (default 1080)")
    parser.add_argument("--height", type=int, default=1440, help="Page height (default 1440)")
    parser.add_argument("--direction", choices=["vertical-rl", "horizontal-lr"], default="vertical-rl", help="Writing direction")
    parser.add_argument("--per-line", type=int, default=None, help="Characters per line (wrapping)")
    parser.add_argument("--punctuation", choices=["break", "omit"], default="break", help="Punctuation policy")
    parser.add_argument("--stroke-seconds", type=float, default=0.18, help="Seconds per stroke")
    parser.add_argument("--gap", type=float, default=0.15, help="Seconds between characters")
    parser.add_argument("--intro", type=float, default=0.5, help="Intro pause in seconds")
    parser.add_argument("--outro", type=float, default=1.0, help="Outro pause in seconds")
    parser.add_argument("--time", type=float, default=None, help="Scene time for still image (defaults to end)")
    parser.add_argument("--fps", type=int, default=24, help="Video frames per second (default 24)")
    parser.add_argument("--speed", type=float, default=1.0, help="Video playback speed multiplier (default 1.0)")
    parser.add_argument("--scale", type=float, default=1.0, help="Global glyph scale (0.8 - 1.2)")
    parser.add_argument("--stretch", type=float, default=1.0, help="Global horizontal stretch (0.9 - 1.1)")
    parser.add_argument("--rotate", type=float, default=0.0, help="Global rotation in degrees (-5.0 - 5.0)")
    parser.add_argument("--paper", type=str, default="#f8f3e9", help="Paper background color (hex or r,g,b)")
    parser.add_argument("--ink", type=str, default="#1c1b18", help="Ink color (hex or r,g,b)")
    parser.add_argument("--mode", choices=["auto", "template", "contact", "font_layers"], default="auto", help="Rendering engine mode")
    parser.add_argument("--font", type=str, default=None, help="Optional font path override for font-derived styles")
    return parser.parse_args(args)


def main(args: Optional[list] = None) -> int:
    parsed = parse_args(args)

    if parsed.list_styles:
        print("kai: template\nyan: template width preset")
        manifest = style_manifest()
        for name, item in manifest["styles"].items():
            print(f"{name}: contact brush, {item.get('characters', 'preset')} glyphs")
        for entry in registered_styles():
            print(f"{entry['style']}: {entry['prepared']} prepared glyphs, extensible font")
        return 0

    if (parsed.text is not None) == (parsed.text_file is not None):
        print("Error: Supply exactly one of --text or --text-file", file=sys.stderr)
        return 1

    if parsed.text is not None:
        text = parsed.text
    else:
        text_path = Path(parsed.text_file)
        if not text_path.exists():
            print(f"Error: Text file not found: {parsed.text_file}", file=sys.stderr)
            return 1
        text = text_path.read_text(encoding="utf-8")

    out_path = Path(parsed.output)
    ext = out_path.suffix.lower()
    if ext not in (".png", ".svg", ".mp4"):
        print(f"Error: Output must end in .png, .svg or .mp4, got {ext}", file=sys.stderr)
        return 1

    if ext == ".mp4" and parsed.time is not None:
        print("Error: --time applies only to still images", file=sys.stderr)
        return 1

    if ext != ".mp4" and (parsed.fps != 24 or parsed.speed != 1.0):
        # Only warn or fail if explicitly set?
        pass

    additional_glyphs = None
    if parsed.glyphs:
        glyphs_path = Path(parsed.glyphs)
        if not glyphs_path.exists():
            print(f"Error: Glyphs file not found: {parsed.glyphs}", file=sys.stderr)
            return 1
        additional_glyphs = json.loads(glyphs_path.read_text(encoding="utf-8"))

    try:
        appearance = Appearance.from_dict({"paper": parsed.paper, "ink": parsed.ink})
        transforms = Transforms(scale=parsed.scale, stretch=parsed.stretch, rotation=parsed.rotate)
        layout_dict = {
            "width": parsed.width,
            "height": parsed.height,
            "direction": parsed.direction,
            "characters_per_line": parsed.per_line,
        }
        timing_dict = {
            "stroke_seconds": parsed.stroke_seconds,
            "character_gap": parsed.gap,
            "intro": parsed.intro,
            "outro": parsed.outro,
        }

        scene_spec = SceneSpec(
            text=text,
            style=parsed.style,
            layout=layout_dict,
            timing=timing_dict,
            punctuation=parsed.punctuation,
            appearance=appearance,
            transforms=transforms,
        )

        scene = create_scene(
            scene_spec,
            font_path=parsed.font,
            glyphs=additional_glyphs,
            fetch_missing=parsed.fetch,
            mode=parsed.mode,
        )

        if scene_spec.omitted:
            print(f"Layout separators (not painted): {json.dumps(scene_spec.omitted, ensure_ascii=False)}")

        if ext == ".mp4":
            count = export_video(scene, out_path, fps=parsed.fps, speed=parsed.speed)
            dur = scene.duration if hasattr(scene, "duration") else scene.plan.duration
            print(f"Wrote {out_path}: {count} frames, {scene.width}x{scene.height}, scene {dur:.2f}s")
        else:
            export_still(scene, out_path, time=parsed.time)
            dur = scene.duration if hasattr(scene, "duration") else scene.plan.duration
            print(f"Wrote {out_path}: {scene.width}x{scene.height}, scene {dur:.2f}s")

        return 0

    except Exception as e:
        print(f"Render failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
