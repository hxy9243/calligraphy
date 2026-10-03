#!/usr/bin/env python3
"""Replay the frozen Spring Dawn stroke-IR example with calligraphy-engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from calligraphy.stroke_ir import render_program, validate_program
from calligraphy.engine_metadata import engine_metadata
from calligraphy.artifact_cache import ArtifactCache


HERE = Path(__file__).resolve().parent
DEFAULT_BUNDLE = HERE / "fixtures" / "chun-xiao-programs.json"
DEFAULT_BANK = HERE / "fixtures" / "32-glyph-bank.json"
PAPER = np.array([241, 234, 216], dtype=np.uint8)
INK = np.array([27, 25, 21], dtype=np.uint8)


def load_bundle(path: Path, cache_db: Path | None = None) -> dict:
    bundle = json.loads(path.read_text())
    if bundle.get("schemaVersion") != "kai-writing-scene/0.1":
        raise ValueError("expected a kai-writing-scene/0.1 replay bundle")
    for entry in bundle["programs"]:
        validate_program(entry["ir"])
    if cache_db is not None:
        cache = ArtifactCache(cache_db)
        content_id = cache.put('kai-writing-scene', bundle)
        bundle = cache.get('kai-writing-scene', content_id)
    return bundle


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Scene:
    def __init__(self, bundle: dict):
        self.bundle = bundle
        self.programs = [entry["ir"] for entry in bundle["programs"]]
        self.width, self.height = bundle["layout"]["canvas"]
        self.total = float(bundle["timing"]["timelineUnits"])
        self.starts = [float(item["startUnits"]) for item in bundle["timing"]["glyphs"]]
        self.durations = [float(item["durationUnits"]) for item in bundle["timing"]["glyphs"]]
        self.placements = bundle["placements"]
        self.completed: dict[tuple[int, int], np.ndarray] = {}

    def glyph(self, program_index: int, progress: float, size: int) -> np.ndarray:
        key = (program_index, size)
        if progress >= 1 and key in self.completed:
            return self.completed[key]
        mask = np.asarray(render_program(self.programs[program_index], progress=progress, size=size))
        if mask.shape != (size, size):
            raise ValueError(f"engine returned {mask.shape}; expected {(size, size)}")
        mask = np.clip(mask, 0, 1)
        if progress >= 1:
            self.completed[key] = mask
        return mask

    def frame(self, progress: float) -> Image.Image:
        elapsed = float(np.clip(progress, 0, 1)) * self.total
        canvas = np.broadcast_to(PAPER, (self.height, self.width, 3)).copy()
        for item, start, duration in zip(self.placements, self.starts, self.durations):
            local = float(np.clip((elapsed - start) / duration, 0, 1))
            if local <= 0:
                continue
            size = int(item["size"])
            mask = self.glyph(int(item["programIndex"]), local, size)[..., None]
            x, y = int(item["x"]), int(item["y"])
            region = canvas[y:y + size, x:x + size]
            region[:] = np.rint(region * (1 - mask) + INK * mask).astype(np.uint8)
        return Image.fromarray(canvas, "RGB")


def write_metadata(bundle_path: Path, output_dir: Path, frame_path: Path, video_path: Path | None) -> None:
    artifacts = {"frame": {"path": frame_path.name, "sha256": sha256(frame_path)}}
    if video_path is not None:
        artifacts["video"] = {"path": video_path.name, "sha256": sha256(video_path)}
    value = {
        "schemaVersion": "kai-stroke-ir-example-output/0.1",
        "generated": True,
        "sourceBundle": {"path": str(bundle_path), "sha256": sha256(bundle_path)},
        "engineEntryPoint": "calligraphy.stroke_ir.render_program",
        "replayEngine": engine_metadata('kai-replay'),
        "artifacts": artifacts,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


def render_video(scene: Scene, path: Path, duration: float, fps: int) -> None:
    frames = round(duration * fps)
    command = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{scene.width}x{scene.height}", "-r", str(fps), "-i", "-", "-an",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
               "-movflags", "+faststart", str(path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        assert process.stdin is not None
        for index in range(frames):
            progress = 1.0 if frames == 1 else index / (frames - 1)
            process.stdin.write(np.asarray(scene.frame(progress)).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError(f"ffmpeg exited with status {process.returncode}")
    except BaseException:
        process.kill()
        process.wait()
        raise


def render_gallery(bank_path: Path, output_dir: Path, size: int, steps: int) -> None:
    """Render seekable inspection frames from the frozen 32-glyph bank."""
    bank = json.loads(bank_path.read_text())
    if bank.get("schemaVersion") != "kai-stroke-ir-example-bank/0.1":
        raise ValueError("expected a kai-stroke-ir-example-bank/0.1 fixture")
    frame_root = output_dir / "gallery"
    entries = []
    for glyph in bank["glyphs"]:
        program = validate_program(glyph["program"])
        character = glyph["character"]
        directory = frame_root / character
        directory.mkdir(parents=True, exist_ok=True)
        frames = []
        for index in range(steps):
            progress = 1.0 if steps == 1 else index / (steps - 1)
            mask = np.asarray(render_program(program, progress=progress, size=size))
            rgb = np.rint(PAPER * (1 - mask[..., None]) + INK * mask[..., None]).astype(np.uint8)
            path = directory / f"{index:02d}.png"
            Image.fromarray(rgb, "RGB").save(path, optimize=True)
            frames.append(str(path.relative_to(output_dir)))
        entries.append({"character": character, "frames": frames,
                        "strokeCount": len(program["strokes"]),
                        "programSha256": glyph["programSha256"],
                        "metrics480": glyph["metrics480"]})
    gallery = {
        "schemaVersion": "kai-stroke-ir-gallery/0.1", "generated": True,
        "sourceBank": {"path": str(bank_path), "sha256": sha256(bank_path)},
        "size": size, "steps": steps, "glyphs": entries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gallery.json").write_text(
        json.dumps(gallery, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("frame", "render", "gallery"))
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--cache-db", type=Path,
                        help="import the selected writing bundle into SQLite on startup")
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    parser.add_argument("--output-dir", type=Path, default=HERE / "work")
    parser.add_argument("--progress", type=float, default=1.0,
                        help="normalized scene progress for frame.png")
    parser.add_argument("--duration", type=float, default=45.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--size", type=int, default=360,
                        help="square gallery frame size")
    parser.add_argument("--steps", type=int, default=31,
                        help="number of seek frames per gallery glyph")
    args = parser.parse_args()
    if args.command == 'gallery' and args.cache_db:
        parser.error('--cache-db applies to frame and render; gallery uses --bank')
    if not 0 <= args.progress <= 1:
        parser.error("--progress must be in [0, 1]")
    if min(args.duration, args.fps, args.size, args.steps) <= 0:
        parser.error("duration, fps, size and steps must be positive")
    return args


def main() -> None:
    args = parse_args()
    if args.command == "gallery":
        render_gallery(args.bank, args.output_dir, args.size, args.steps)
        print(args.output_dir / "gallery.json")
        return
    scene = Scene(load_bundle(args.bundle, args.cache_db))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame_path = args.output_dir / "frame.png"
    scene.frame(args.progress).save(frame_path, optimize=True)
    video_path = None
    if args.command == "render":
        video_path = args.output_dir / "writing.mp4"
        render_video(scene, video_path, args.duration, args.fps)
    write_metadata(args.bundle, args.output_dir, frame_path, video_path)
    print(args.output_dir / "manifest.json")


if __name__ == "__main__":
    main()
