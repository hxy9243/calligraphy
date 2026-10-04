"""Background worker for rendering Calligraphy Studio jobs."""
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from calligraphy.renderer import create_scene, export_still, export_svg, export_video
from calligraphy.spec import Appearance, SceneSpec, Transforms
from .database import Database, get_db
from .style_catalog import downloaded_catalog_entry

logger = logging.getLogger("calligraphy.worker")


def _auto_prepare_font(style: str, text: str) -> None:
    """If style is not registered but exists in data/fonts catalog, auto-prepare on demand."""
    if style in ("kai", "yan"):
        return
    from calligraphy.font_pipeline import style_path, prepare_style
    from calligraphy.text.glyphs import resolve_glyphs
    import json

    try:
        spath = style_path(style)
        if spath.exists():
            return
    except Exception:
        return

    catalog_path = Path(__file__).resolve().parent.parent / "data" / "calligraphy_fonts.json"
    if not catalog_path.exists():
        return

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception:
        return

    clean_style = style.strip()
    entry = downloaded_catalog_entry(catalog, clean_style)
    if not entry:
        return

    rel_path = entry.get("file_path")
    if not rel_path:
        return

    font_file = Path(__file__).resolve().parent.parent / rel_path
    if not font_file.exists():
        return

    licenses_dir = Path(__file__).resolve().parent.parent / "data" / "licenses"
    license_type = (entry.get("license") or "").lower()
    if entry.get("license_path"):
        license_path = Path(__file__).resolve().parent.parent / entry["license_path"]
    elif "gpl" in license_type or "wang" in clean_style or "hanwang" in clean_style:
        license_path = licenses_dir / "WangFonts-GPL.txt"
    elif "arphic" in clean_style:
        license_path = licenses_dir / "Arphic-License.txt"
    else:
        license_path = licenses_dir / "MaShanZheng.ttf.OFL.txt"

    try:
        needed_glyphs = resolve_glyphs(text, fetch_missing=True)
        prepare_style(
            clean_style,
            needed_glyphs,
            font_path=str(font_file),
            license_path=str(license_path) if license_path.exists() else None,
            source=entry.get("source_url") or "",
        )
        logger.info("Auto-prepared style %s for text %s", clean_style, text)
    except Exception as exc:
        logger.warning("Auto-prepare failed for style %s: %s", clean_style, exc)


def execute_job(job: Dict[str, Any], db: Database) -> bool:
    job_id = job["job_id"]
    text = job["text"]
    style = job["style"]
    params = job.get("params", {})
    job_type = job["job_type"]

    logger.info("Executing job %s (type: %s, style: %s)", job_id, job_type, style)
    db.update_job(job_id, status="rendering", progress=0.1)

    try:
        # Default geometry & timing
        layout_dict = {
            "width": params.get("width", 720),
            "height": params.get("height", 960),
            "direction": params.get("direction", "vertical-rl"),
            "characters_per_line": params.get("characters_per_line", None),
            "gap": float(params.get("spacing", params.get("gap", 0.18))),
        }
        timing_dict = {
            "stroke_seconds": params.get("stroke_seconds", 0.18),
            "character_gap": params.get("character_gap", 0.15),
            "intro": params.get("intro", 0.5),
            "outro": params.get("outro", 1.0),
        }
        appearance = Appearance.from_dict({
            "paper": params.get("paper", "#f8f3e9"),
            "ink": params.get("ink", "#1c1b18"),
        })
        transforms = Transforms(
            scale=params.get("scale", 1.0),
            stretch=params.get("stretch", 1.0),
            rotation=params.get("rotation", 0.0),
        )

        scene_spec = SceneSpec(
            text=text,
            style=style,
            layout=layout_dict,
            timing=timing_dict,
            punctuation=params.get("punctuation", "break"),
            appearance=appearance,
            transforms=transforms,
        )

        db.update_job(job_id, progress=0.3)

        _auto_prepare_font(style, text)

        scene = create_scene(scene_spec, fetch_missing=True)

        db.update_job(job_id, progress=0.5)

        base_output_dir = Path("outputs").resolve()
        if job_type == "preview":
            out_dir = base_output_dir / "previews"
            out_dir.mkdir(parents=True, exist_ok=True)
            requested_format = params.get("format", "auto")
            if requested_format == "png":
                out_file = out_dir / f"{job_id}.png"
                export_still(scene, out_file)
            elif hasattr(scene, "frame_svg"):
                out_file = out_dir / f"{job_id}.svg"
                export_svg(scene, out_file)
            else:
                out_file = out_dir / f"{job_id}.png"
                export_still(scene, out_file)
        else:
            out_dir = base_output_dir / "videos"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{job_id}.mp4"
            fps = int(params.get("fps", 24))
            speed = float(params.get("speed", 1.0))
            export_video(scene, out_file, fps=fps, speed=speed)

        db.update_job(
            job_id,
            status="succeeded",
            progress=1.0,
            output_path=str(out_file),
            completed=True,
        )
        logger.info("Job %s succeeded: %s", job_id, out_file)
        return True
    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        db.update_job(
            job_id,
            status="failed",
            error_message=str(exc),
            completed=True,
        )
        return False


class BackgroundTaskRunner:
    """In-process thread worker queue for immediate local development."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_db()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cond = threading.Condition()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def notify(self) -> None:
        with self._cond:
            self._cond.notify()

    def stop(self) -> None:
        self._running = False
        with self._cond:
            self._cond.notify_all()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while self._running:
            job = self.db.claim_next_job()
            if job:
                execute_job(job, self.db)
            else:
                with self._cond:
                    if self._running:
                        self._cond.wait(timeout=1.0)


_RUNNER_INSTANCE: Optional[BackgroundTaskRunner] = None


def get_runner() -> BackgroundTaskRunner:
    global _RUNNER_INSTANCE
    if _RUNNER_INSTANCE is None:
        _RUNNER_INSTANCE = BackgroundTaskRunner()
    return _RUNNER_INSTANCE


def run_worker_loop(db_url: Optional[str] = None) -> None:
    """CLI worker entry point."""
    db = get_db(db_url)
    print(f"Starting Calligraphy Worker on {db.db_url}...", file=sys.stderr)
    try:
        while True:
            job = db.claim_next_job()
            if job:
                execute_job(job, db)
            else:
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("Worker stopped.", file=sys.stderr)


if __name__ == "__main__":
    run_worker_loop()
