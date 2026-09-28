"""Background worker for rendering Calligraphy Studio jobs."""
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from calligraphy.renderer import create_scene, export_still, export_video
from calligraphy.spec import Appearance, SceneSpec, Transforms
from .database import Database, get_db

logger = logging.getLogger("calligraphy.worker")


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

        scene = create_scene(scene_spec, fetch_missing=True)

        db.update_job(job_id, progress=0.5)

        base_output_dir = Path("outputs").resolve()
        if job_type == "preview":
            out_dir = base_output_dir / "previews"
            out_dir.mkdir(parents=True, exist_ok=True)
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
