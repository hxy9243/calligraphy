"""Background worker for rendering Calligraphy Studio jobs."""
import logging
import os
import sys
import threading
import time
import fcntl
import math
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from calligraphy.renderer import create_scene, export_still, export_svg, export_video
from .composition import scene_spec_from_params
from .database import Database, get_db
from .style_catalog import downloaded_catalog_entry

logger = logging.getLogger("calligraphy.worker")
_RENDER_SLOT = threading.Lock()
_PROCESSES = {}
_PROCESSES_LOCK = threading.Lock()


def output_root():
    return Path(os.environ.get("CALLIGRAPHY_OUTPUT_DIR", "outputs")).resolve()


def execute_job_bounded(job, db):
    """One compute slot, with a killable process and deadline in deployment."""
    wait = 5 if job["job_type"] == "preview" else 650
    if not _RENDER_SLOT.acquire(timeout=wait):
        db.update_job(job["job_id"], status="failed", completed=True,
                      error_message="服务器正在处理任务，请稍后再试 / Renderer busy; please retry.")
        return False
    try:
        if os.environ.get("CALLIGRAPHY_ISOLATE_JOBS") != "1":
            return execute_job(job, db)
        deadline = int(os.environ.get("CALLIGRAPHY_JOB_TIMEOUT_SECONDS", "600"))
        process = subprocess.Popen([sys.executable, "-m", "backend.worker", "--job-id", job["job_id"], "--database", db.db_url], start_new_session=True)
        with _PROCESSES_LOCK:
            _PROCESSES[job["job_id"]] = (process, db)
        try:
            process.wait(timeout=deadline)
        except subprocess.TimeoutExpired:
            # Kill the encoder as well as the renderer; threads cannot do this.
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError("任务超时，请缩短文本后重试 / Render exceeded its time limit.")
        finished = db.get_job(job["job_id"])
        if finished and finished["status"] == "failed":
            return False
        if process.returncode != 0 or finished["status"] not in ("succeeded", "failed"):
            raise RuntimeError("渲染进程中断，请重试 / Render process interrupted; please retry.")
        return finished["status"] == "succeeded"
    except Exception as exc:
        logger.exception("Isolated job failed")
        db.update_job(job["job_id"], status="failed", completed=True, error_message=str(exc))
        return False
    finally:
        with _PROCESSES_LOCK:
            _PROCESSES.pop(job["job_id"], None)
        _RENDER_SLOT.release()


def cleanup_expired_outputs(db):
    cutoff = time.time() - int(os.environ.get("CALLIGRAPHY_RETENTION_SECONDS", "86400"))
    root = output_root()
    # Hold SQLite's write reservation through unlink: share issuance validates
    # and grants its lease in the same kind of transaction, across DB instances.
    with db.retention_cleanup(datetime.fromtimestamp(cutoff, timezone.utc).isoformat()) as protected:
        # Include orphaned outputs whose history was explicitly deleted.
        for folder in ("previews", "videos"):
            for path in (root / folder).glob("*"):
                if path.is_file() and not path.is_symlink() and path.resolve() not in protected and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)


def _auto_prepare_font(style: str, text: str) -> None:
    """If style is not registered but exists in data/fonts catalog, auto-prepare on demand."""
    if style in ("kai", "yan", "lishu", "liu", "yan-contact"):
        return
    from calligraphy.font_pipeline import style_path, prepare_style
    from calligraphy.text.glyphs import resolve_glyphs
    import json

    spath = style_path(style)
    if spath.exists():
        return

    catalog_path = Path(__file__).resolve().parent.parent / "data" / "calligraphy_fonts.json"
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    clean_style = style.strip()
    entry = downloaded_catalog_entry(catalog, clean_style)
    if not entry:
        raise ValueError(f"Font is not registered or available in the catalog: {clean_style}")

    rel_path = entry.get("file_path")
    if not rel_path:
        raise ValueError(f"Font catalog entry has no source file: {clean_style}")

    font_file = Path(__file__).resolve().parent.parent / rel_path
    if not font_file.exists():
        raise FileNotFoundError(f"Font source file is missing for {clean_style}: {rel_path}")

    licenses_dir = Path(__file__).resolve().parent.parent / "data" / "licenses"
    license_type = (entry.get("license") or "").lower()
    demo_licenses = {"mashanzheng": "MaShanZheng.ttf.OFL.txt",
                     "longcang": "LongCang.ttf.OFL.txt",
                     "lxgw-wenkai-tc": "LXGWWenKaiTC-OFL.txt",
                     "zhimang-xingshu": "ZhiMangXing.ttf.OFL.txt",
                     "edukai": "EduKai-License.txt", "tw-kai": "TW-Kai-License.txt",
                     "tw-sung": "TW-Sung-License.txt", "genryu-min": "GenRyuMin-OFL.txt",
                     "genwan-min": "GenWanMin-OFL.txt", "xiaolai-kai": "Xiaolai-OFL.txt",
                     "cwtex-fangsong": "cwTeXFangSong-GPL.txt"}
    if clean_style in demo_licenses:
        license_path = licenses_dir / demo_licenses[clean_style]
    elif clean_style.startswith("hanwang-") or clean_style == "lishu hanwang":
        license_path = licenses_dir / "WangFonts-GPL.txt"
    elif "arphic" in clean_style:
        license_path = licenses_dir / "Arphic-License.txt"
    elif "shutifang" in clean_style or "liugongquan" in clean_style:
        license_path = licenses_dir / "ShuTiFang-License.txt"
    else:
        # Preserve this font's embedded notices; never attribute another font's OFL.
        license_path = Path(__file__).resolve().parent.parent / entry["license_path"]

    try:
        needed_glyphs = resolve_glyphs(text, fetch_missing=True)
        prepare_style(
            clean_style,
            needed_glyphs,
            font_path=str(font_file),
            license_path=str(license_path) if license_path.exists() else None,
            source=entry.get("source_url") or "",
        )
        logger.info("Auto-prepared style %s", clean_style)
    except Exception as exc:
        raise ValueError(f"字體筆畫準備失敗 / Font preparation failed for {clean_style}: {exc}") from exc


def execute_job(job: Dict[str, Any], db: Database) -> bool:
    job_id = job["job_id"]
    text = job["text"]
    style = job["style"]
    params = job.get("params", {})
    job_type = job["job_type"]

    logger.info("Executing job %s (type: %s, style: %s)", job_id, job_type, style)
    db.update_job(job_id, status="rendering", progress=0.1)

    try:
        scene_spec = scene_spec_from_params(text, style, params)

        db.update_job(job_id, progress=0.3)

        _auto_prepare_font(style, text)

        scene = create_scene(scene_spec, fetch_missing=True)

        db.update_job(job_id, progress=0.5)

        base_output_dir = output_root()
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
            duration = scene.duration if hasattr(scene, "duration") else scene.plan.duration
            if duration / speed > 120 or math.ceil(duration * fps / speed) > 3000:
                raise ValueError("视频超过 120 秒或 3000 帧，请缩短文本或加快速度 / Video exceeds 120 seconds or 3000 frames.")
            export_video(scene, out_file, fps=fps, speed=speed)

        db.update_job(
            job_id,
            status="succeeded",
            progress=1.0,
            output_path=str(out_file),
            warning_message=getattr(scene, "render_warning", None),
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
        self._lease_file = None

    def start(self) -> None:
        if self._running:
            return
        self._lease_file = self.db.sqlite_path.with_suffix(".worker.lock").open("a")
        try:
            fcntl.flock(self._lease_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lease_file.close()
            self._lease_file = None
            raise RuntimeError("Only one studio instance may use this SQLite volume.")
        self.db.recover_interrupted_jobs()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def notify(self) -> None:
        with self._cond:
            self._cond.notify()

    def stop(self) -> None:
        self._running = False
        with _PROCESSES_LOCK:
            for job_id, (process, db) in list(_PROCESSES.items()):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                db.update_job(job_id, status="failed", completed=True,
                              error_message="服务正在重启，请重试 / Service is restarting; please retry.")
        with self._cond:
            self._cond.notify_all()
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._lease_file and not self._thread.is_alive():
            self._lease_file.close()
            self._lease_file = None

    def is_healthy(self):
        return self._running and self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        last_cleanup = 0
        while self._running:
            try:
                if time.monotonic() - last_cleanup > 60:
                    cleanup_expired_outputs(self.db)
                    last_cleanup = time.monotonic()
                job = self.db.claim_next_job()
                if job:
                    execute_job_bounded(job, self.db)
                else:
                    with self._cond:
                        if self._running:
                            self._cond.wait(timeout=1.0)
            except Exception:
                logger.exception("Worker queue error")
                time.sleep(1)


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
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id")
    parser.add_argument("--database")
    args = parser.parse_args()
    if args.job_id:
        db = Database(args.database)
        job = db.get_job(args.job_id)
        sys.exit(0 if job and execute_job(job, db) else 1)
    else:
        # Use the same exclusive lease, recovery and bounded execution as the API.
        runner = BackgroundTaskRunner(Database(args.database))
        runner.start()
        try:
            while runner.is_healthy():
                time.sleep(1)
        except KeyboardInterrupt:
            runner.stop()
