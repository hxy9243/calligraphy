import json
import hashlib
import secrets
import time
import re
import math
import threading
from collections import deque
from datetime import datetime, timezone
from urllib.parse import parse_qs
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from fastapi import Cookie, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from calligraphy.font_pipeline import registered_styles
from calligraphy.text.converter import ConversionUnavailableError, convert_text
from calligraphy.text.input import parse_text
from .database import Database, get_db
from .database import AdmissionError
from .public_fonts import allowed_style, public_catalog, private_catalog, validate_style, font_sample
from .style_catalog import STYLE_ALIASES
from .worker import execute_job_bounded as execute_job, get_runner
from .editor_preview import editor_preview

MAX_INPUT_CHARACTERS = 256
MAX_LINE_CHARACTERS = 20

class ConvertRequest(BaseModel):
    text: str
    target: Literal["simp", "trad", "zh-hans", "zh-hant"] = "trad"


class PreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARACTERS)
    style: str = Field(default="kai")
    direction: Literal["vertical-rl", "horizontal-lr"] = "vertical-rl"
    palette: Literal["light", "dark"] = "light"
    format: str = Field(default="auto")
    spacing: float = Field(default=0.18, ge=0.0, le=2.0)
    punctuation: str = Field(default="omit")
    width: Optional[int] = Field(default=None, ge=64, le=2400)
    height: Optional[int] = Field(default=None, ge=64, le=2400)
    # None retains legacy whole-page fitting for older clients and saved jobs.
    font_size: Optional[int] = Field(default=None, ge=8, le=160)
    fit: bool = True

    @model_validator(mode="after")
    def bounded_canvas(self):
        if (self.width or 720) * (self.height or 960) > 2400 * 1280:
            raise ValueError("畫布面積過大 / Canvas must not exceed 3,072,000 pixels.")
        return self

    @field_validator("text")
    @classmethod
    def validate_line_length(cls, v: str) -> str:
        for idx, line in enumerate(v.split("\n"), 1):
            if len(line) > MAX_LINE_CHARACTERS:
                raise ValueError(
                    f"第 {idx} 行超出单行 {MAX_LINE_CHARACTERS} 字限制（当前 {len(line)} 字），请换行后再试 / Line {idx} exceeds {MAX_LINE_CHARACTERS}-character limit ({len(line)} chars)."
                )
        return v


class EditorPreviewRequest(PreviewRequest):
    width: int = Field(default=480, ge=64, le=2400)
    height: int = Field(default=640, ge=64, le=2400)
    font_size: int = Field(default=48, ge=8, le=160)
    fit: bool = True


class RenderRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARACTERS)
    style: str = Field(default="kai")
    direction: Literal["vertical-rl", "horizontal-lr"] = "vertical-rl"
    palette: Literal["light", "dark"] = "light"
    fps: int = Field(default=24, ge=1, le=60)
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    spacing: float = Field(default=0.18, ge=0.0, le=2.0)
    punctuation: str = Field(default="omit")
    width: Optional[int] = Field(default=None, ge=64, le=2400)
    height: Optional[int] = Field(default=None, ge=64, le=2400)
    # None retains legacy whole-page fitting for older clients and saved jobs.
    font_size: Optional[int] = Field(default=None, ge=8, le=160)
    fit: bool = True

    @model_validator(mode="after")
    def bounded_canvas(self):
        if (self.width or 720) * (self.height or 960) > 2400 * 1280:
            raise ValueError("畫布面積過大 / Canvas must not exceed 3,072,000 pixels.")
        return self

    @field_validator("width", "height")
    @classmethod
    def even_dimensions(cls, value):
        if value is not None and value % 2:
            raise ValueError("视频尺寸须为偶数 / Video dimensions must be even.")
        return value

    @field_validator("text")
    @classmethod
    def validate_line_length(cls, v: str) -> str:
        for idx, line in enumerate(v.split("\n"), 1):
            if len(line) > MAX_LINE_CHARACTERS:
                raise ValueError(
                    f"第 {idx} 行超出单行 {MAX_LINE_CHARACTERS} 字限制（当前 {len(line)} 字），请换行后再试 / Line {idx} exceeds {MAX_LINE_CHARACTERS}-character limit ({len(line)} chars)."
                )
        return v


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background worker runner on startup
    runner = get_runner()
    runner.start()
    yield
    runner.stop()


app = FastAPI(
    title="Calligraphy Studio API",
    description="Render Chinese calligraphy text into stills and videos.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    for err in exc.errors():
        if err.get("type") == "string_too_long":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": f"输入文本长度超出 {MAX_INPUT_CHARACTERS} 字符上限，请调整后再试 / Text exceeds the {MAX_INPUT_CHARACTERS}-character limit."
                },
            )
        if err.get("type") == "string_too_short":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "输入文本不能为空 / Text must not be empty."
                },
            )
        if err.get("type") == "value_error":
            msg = err.get("msg", "")
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": msg},
            )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )

@app.exception_handler(AdmissionError)
async def admission_error(request, exc):
    return JSONResponse(status_code=429, content={"detail": str(exc)}, headers={"Retry-After": str(exc.retry_after)})


def checked_style(style):
    try:
        return validate_style(style)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


SESSION_COOKIE_NAME = "calligraphy_session"


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    public_capability = request.url.path.startswith(("/api/exports/", "/api/shares/")) or request.url.path in (
        "/export.html", "/export.js", "/export.css", "/watch.html", "/watch.js", "/watch.css",
    )
    capability_response = public_capability or request.url.path.endswith(("/export-link", "/share-link", "/share-link/status"))
    # Browser mutations are same-origin. Railway terminates TLS before forwarding.
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        from urllib.parse import urlsplit
        if urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse(status_code=403, content={"detail": "Cross-origin request denied."}, headers=EXPORT_HEADERS if capability_response else None)
    # Capabilities never become browser sessions and never grant history access.
    if public_capability:
        response = await call_next(request)
        response.headers.update(EXPORT_HEADERS)
        return response
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    is_new = False
    if not session_id or len(session_id) > 64:
        session_id = uuid.uuid4().hex
        is_new = True
    request.state.session_id = session_id
    db = get_db()
    db.touch_session(session_id)

    response = await call_next(request)
    if capability_response:
        response.headers.update(EXPORT_HEADERS)
    if is_new:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=7 * 86400,
            secure=os.environ.get("CALLIGRAPHY_SECURE_COOKIES") == "1",
        )
    return response


@app.get("/api/styles")
def list_styles():
    """List available writing styles (fixed collection fonts removed)."""
    styles = [
        {"id": "kai", "name": "楷書 (Kai)", "description": "Fitted stroke writing / 擬合筆畫書寫", "type": "stroke_ir"},
        {"id": "yan", "name": "顏體 (Yan)", "description": "Yan-inspired fitted contact strokes", "type": "stroke_ir"},
    ]
    font_names = {
        "mashanzheng": "鐘齊馬善政毛筆楷書 (Ma Shan Zheng)",
        "i-yan-kai": "刻石錄顏體 (I.Yan Kai)",
        "qiji-kai": "令東齊伋體楷書 (LingDong Qiji Kai)",
        "chill-qiuhong-kai": "寒蟬秋鴻楷書 (Chill QiuHong Kai)",
        "longcang": "龍藏體 (Long Cang)",
        "lishu hanwang": "王漢宗中隸書 (HanWang LiSu)",
        "aa shoujin": "瘦金體 (Shoujin)",
        "chiron-goround": "昭源黑體 (Chiron GoRound)",
        "tw-sung": "全字庫正宋體 (TW-Sung)",
        "genryu-min": "源流明體 (GenRyuMin)",
        "genwan-min": "源雲明體 (GenWanMin)",
        "cwtex-fangsong": "cwTeX 仿宋體 (cwTeX FangSong)",
        "hanwang-shinsu": "王漢宗中新書繁 (HanWang ShinSu)",
        "shutifang-liugongquan-kai": "書體坊柳公權楷 (ShuTiFang Liu GongQuan)",
    }
    for entry in registered_styles():
        if not allowed_style(entry["style"]):
            continue
        display_name = font_names.get(entry["style"], entry["style"])
        styles.append({
            "id": entry["style"],
            "name": display_name,
            "description": f"{entry['prepared']} prepared glyphs, extensible font",
            "type": "font",
        })
    known = {s["id"] for s in styles}
    for entry in private_catalog():
        canonical = STYLE_ALIASES.get(entry["id"], entry["id"])
        if allowed_style(canonical) and entry.get("is_downloaded") == 1 and canonical not in known:
            styles.append({"id": canonical, "name": entry["name_zh"], "description": "Font-derived writing / 字体推断书写", "type": "font"})
            known.add(canonical)
    return {"styles": [s for s in styles if allowed_style(s["id"])]}


@app.post("/api/convert-script")
def convert_script_endpoint(req: ConvertRequest):
    """Convert text between Traditional and Simplified Chinese."""
    try:
        converted = convert_text(req.text, req.target)
    except ConversionUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"text": converted, "target": req.target}


@app.get("/api/font-catalog")
@app.get("/fonts.json")
def get_font_catalog():
    return JSONResponse(content=public_catalog())


@app.get("/api/font-samples/{style}")
def sample_font(style: str):
    if not allowed_style(style):
        raise HTTPException(status_code=404, detail="Font sample not available.")
    try:
        pixels = font_sample(style)
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="Font sample not available.")
    return Response(pixels, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/health")
def health():
    get_db()._get_sqlite_conn().execute("SELECT 1").fetchone()
    runner = get_runner()
    if not runner.is_healthy():
        raise HTTPException(status_code=503, detail="Render worker unavailable.")
    return {"status": "ok"}


@app.post("/api/previews")
def generate_preview(req: PreviewRequest, request: Request, response: Response):
    """Generate a quick still preview."""
    session_id = request.state.session_id
    chosen_punct = req.punctuation if req.punctuation in ("break", "omit") else "omit"
    try:
        parsed = parse_text(req.text, punctuation=chosen_punct)
        if len(parsed["characters"]) > MAX_INPUT_CHARACTERS:
            raise HTTPException(
                status_code=400,
                detail=f"输入包含 {len(parsed['characters'])} 个汉字，超出单次 {MAX_INPUT_CHARACTERS} 汉字上限 / Hanzi character count ({len(parsed['characters'])}) exceeds the {MAX_INPUT_CHARACTERS}-character limit.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = f"prev_{uuid.uuid4().hex[:12]}"
    db = get_db()
    chosen_style = checked_style(req.style)
    params = {
        "format": req.format,
        "spacing": req.spacing,
        "direction": req.direction,
        "palette": req.palette,
        "font_size": req.font_size,
        "fit": req.fit,
        "punctuation": chosen_punct,
    }
    if req.width:
        params["width"] = req.width
    if req.height:
        params["height"] = req.height

    job = db.create_job(
        job_id=job_id,
        session_id=session_id,
        job_type="preview",
        text=req.text,
        style=chosen_style,
        params=params,
        status="rendering",
        admit=True,
    )
    # Execute preview immediately for snappy preview response
    success = execute_job(job, db)
    if not success:
        failed_job = db.get_job(job_id)
        raise HTTPException(
            status_code=422,
            detail=failed_job.get("error_message") or "Preview rendering failed",
        )

    finished = db.get_job(job_id)
    out_path = finished.get("output_path") if finished else None
    svg_content = None
    if out_path and out_path.endswith(".svg"):
        try:
            svg_content = Path(out_path).read_text(encoding="utf-8")
        except Exception:
            pass

    return {
        "job_id": job_id,
        "svg": svg_content,
        "preview_url": f"/api/jobs/{job_id}/image",
        "warning_message": finished.get("warning_message") if finished else None,
    }


@app.post("/api/editor-preview")
def render_editor_preview(req: EditorPreviewRequest):
    params = req.model_dump()
    params['style'] = checked_style(req.style)
    try:
        params['lines'] = parse_text(req.text, punctuation=req.punctuation)['lines']
        pixels = editor_preview(params)
    except BlockingIOError as exc:
        raise HTTPException(status_code=503, detail=str(exc), headers={'Retry-After': '2'})
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return Response(pixels, media_type='image/png', headers={'Cache-Control': 'no-store'})


@app.post("/api/renders", status_code=status.HTTP_202_ACCEPTED)
def submit_render(req: RenderRequest, request: Request, response: Response):
    """Submit asynchronous video generation job."""
    session_id = request.state.session_id
    chosen_punct = req.punctuation if req.punctuation in ("break", "omit") else "omit"
    try:
        parsed = parse_text(req.text, punctuation=chosen_punct)
        if len(parsed["characters"]) > MAX_INPUT_CHARACTERS:
            raise HTTPException(
                status_code=400,
                detail=f"输入包含 {len(parsed['characters'])} 个汉字，超出单次 {MAX_INPUT_CHARACTERS} 汉字上限 / Hanzi character count ({len(parsed['characters'])}) exceeds the {MAX_INPUT_CHARACTERS}-character limit.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    job_id = f"vid_{uuid.uuid4().hex[:12]}"
    db = get_db()
    chosen_style = checked_style(req.style)
    params = {
        "fps": req.fps,
        "speed": req.speed,
        "spacing": req.spacing,
        "direction": req.direction,
        "palette": req.palette,
        "font_size": req.font_size,
        "fit": req.fit,
        "punctuation": chosen_punct,
    }
    if req.width:
        params["width"] = req.width
    if req.height:
        params["height"] = req.height

    job = db.enqueue_render(
        job_id=job_id,
        session_id=session_id,
        text=req.text,
        style=chosen_style,
        params=params,
        admit=True,
    )
    runner = get_runner()
    runner.notify()

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "message": "Video render accepted",
    }


def job_retention_summary(job, db, retention_seconds):
    """Describe cleanup timing, never the lifetime of an access capability.

    History and files age independently; the earlier deadline limits the work.
    A live share lease protects both. Export capabilities do not retain either.
    The worker cleans asynchronously, so this is a cleanup eligibility deadline,
    not a promise that every owner URL becomes unavailable at this instant.
    """
    summary = {"expires_at": None, "ordinary_expires_at": None,
               "share_expires_at": None, "output_available": None}
    if job["status"] not in ("succeeded", "failed"):
        return summary
    completed = datetime.fromisoformat(job.get("completed_at") or job["created_at"]).timestamp()
    ordinary = completed + retention_seconds
    if job["status"] == "succeeded":
        path = Path(job["output_path"]) if job.get("output_path") else None
        try:
            available = path is not None and not path.is_symlink() and path.is_file()
            if available:
                ordinary = min(ordinary, path.stat().st_mtime + retention_seconds)
        except OSError:
            available = False
        summary["output_available"] = available
    share = db.get_video_share(job["job_id"]) if job["status"] == "succeeded" and job["job_type"] == "render" else None
    lease = share["expires_at"] if share and share["expires_at"] > time.time() else None
    summary.update(ordinary_expires_at=ordinary, share_expires_at=lease,
                   expires_at=max(ordinary, lease) if lease is not None else ordinary)
    return summary


@app.get("/api/jobs")
def list_session_jobs(request: Request, response: Response):
    """List all jobs for current browser session."""
    session_id = request.state.session_id
    db = get_db()
    jobs = db.list_jobs(session_id)
    retention_seconds = int(os.environ.get("CALLIGRAPHY_RETENTION_SECONDS", "86400"))
    for j in jobs:
        j["retention"] = job_retention_summary(j, db, retention_seconds)
        if j.get("status") == "succeeded" and j.get("job_type") == "render":
            j["download_url"] = f"/api/jobs/{j['job_id']}/download"
            j["video_url"] = f"/api/jobs/{j['job_id']}/video"
        elif j.get("status") == "succeeded" and j.get("job_type") == "preview":
            j["download_url"] = f"/api/jobs/{j['job_id']}/image"
    return {"jobs": jobs, "retention_seconds": retention_seconds}


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_history_job(job_id: str, request: Request):
    result = get_db().delete_history_job(job_id, request.state.session_id)
    if result == "missing":
        raise HTTPException(status_code=404, detail="Job not found")
    if result == "active":
        raise HTTPException(status_code=409, detail="任务正在生成，请完成后再删除")
    return Response(status_code=204)


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str, request: Request, response: Response):
    """Get status and details of a job."""
    session_id = request.state.session_id
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Job not found")

    download_url = None
    video_url = None
    if job["status"] == "succeeded" and job["job_type"] == "render":
        download_url = f"/api/jobs/{job_id}/download"
        video_url = f"/api/jobs/{job_id}/video"
    elif job["status"] == "succeeded" and job["job_type"] == "preview":
        download_url = f"/api/jobs/{job_id}/image"

    return {
        "job_id": job["job_id"],
        "job_type": job["job_type"],
        "status": job["status"],
        "progress": job.get("progress", 0.0),
        "text": job["text"],
        "style": job["style"],
        "error_message": job.get("error_message"),
        "warning_message": job.get("warning_message"),
        "download_url": download_url,
        "video_url": video_url,
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "retention": job_retention_summary(job, db, int(os.environ.get("CALLIGRAPHY_RETENTION_SECONDS", "86400"))),
    }


@app.get("/api/jobs/{job_id}/video")
def get_job_video(job_id: str, request: Request, response: Response):
    """Stream or view completed video file inline."""
    session_id = request.state.session_id
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "succeeded" or not job.get("output_path"):
        raise HTTPException(status_code=400, detail="Job not completed")

    file_path = Path(job["output_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file missing")

    return FileResponse(
        str(file_path),
        media_type="video/mp4",
    )


@app.get("/api/jobs/{job_id}/download")
def download_video(job_id: str, request: Request, response: Response):
    """Download completed video file."""
    session_id = request.state.session_id
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "succeeded" or not job.get("output_path"):
        raise HTTPException(status_code=400, detail="Job not completed")

    file_path = Path(job["output_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file missing")

    filename = f"calligraphy_{job['style']}_{job_id[:8]}.mp4"
    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        filename=filename,
    )


@app.get("/api/jobs/{job_id}/image")
def get_job_image(job_id: str, request: Request, response: Response):
    """Get still preview image."""
    session_id = request.state.session_id
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "succeeded" or not job.get("output_path"):
        raise HTTPException(status_code=400, detail="Preview not completed")

    file_path = Path(job["output_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Preview file missing")

    media_type = "image/svg+xml" if file_path.suffix.lower() == ".svg" else "image/png"
    return FileResponse(
        str(file_path),
        media_type=media_type,
    )


EXPORT_HEADERS = {
    "Cache-Control": "private, no-store",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
}
EXPORT_TTL_SECONDS = 600


def export_video_path(job, lease_expires=None):
    """Validate the sole artifact a capability may release, including retention."""
    if not job or job["job_type"] != "render" or job["status"] != "succeeded" or not job.get("output_path"):
        raise HTTPException(404, "影片尚未完成或已移除 / Video unavailable")
    path = Path(job["output_path"])
    if path.suffix.lower() != ".mp4" or path.is_symlink() or not path.is_file():
        raise HTTPException(404, "影片檔案已移除 / Video unavailable")
    retention = min(86400, int(os.environ.get("CALLIGRAPHY_RETENTION_SECONDS", "86400")))
    completed = datetime.fromisoformat(job["completed_at"] or job["created_at"]).timestamp()
    deadline = min(completed, path.stat().st_mtime) + retention
    # Explicit sharing may retain this one file longer. Callers supply the
    # current lease; this helper performs no nested database access.
    if lease_expires is not None and lease_expires > time.time():
        deadline = max(deadline, lease_expires)
    if deadline <= time.time():
        raise HTTPException(404, "影片已到期 / Video expired")
    return path, deadline


@app.post("/api/jobs/{job_id}/export-link")
def create_video_export(job_id: str, request: Request):
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != request.state.session_id:
        raise HTTPException(404, "Job not found")
    share = db.get_video_share(job_id)
    _, deadline = export_video_path(job, share["expires_at"] if share else None)
    token = secrets.token_urlsafe(32)
    expires = min(time.time() + EXPORT_TTL_SECONDS, deadline)
    if not db.set_video_export(job_id, request.state.session_id, hashlib.sha256(token.encode()).hexdigest(), expires):
        raise HTTPException(404, "Job not found")
    # Fragment stays out of access logs and Referer headers. No cookie transfer.
    return JSONResponse({"url": f"/export.html#{job_id}.{token}", "expires_at": expires}, headers=EXPORT_HEADERS)


@app.delete("/api/jobs/{job_id}/export-link", status_code=204)
def revoke_video_export(job_id: str, request: Request):
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != request.state.session_id:
        raise HTTPException(404, "Job not found")
    db.revoke_video_export(job_id)
    return Response(status_code=204, headers=EXPORT_HEADERS)


EXPORT_COOKIE_NAME = "calligraphy_video_export"


def checked_video_export(job_id, token):
    if not SHARE_ID.fullmatch(job_id) or not isinstance(token, str) or not SHARE_TOKEN.fullmatch(token):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    db = get_db()
    capability = db.get_video_export(job_id)
    if not capability or capability["expires_at"] <= time.time() or not secrets.compare_digest(
        capability["token_hash"], hashlib.sha256(token.encode("ascii")).hexdigest()
    ):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    share = db.get_video_share(job_id)
    try:
        path, deadline = export_video_path(db.get_job(job_id), share["expires_at"] if share else None)
    except (HTTPException, OSError, ValueError, TypeError):
        raise HTTPException(404, SHARE_UNAVAILABLE) from None
    return path, min(capability["expires_at"], deadline)


@app.post("/api/exports/{job_id}/download")
async def download_video_export(job_id: str, request: Request):
    # Legacy body-token API. Browser viewers use access + native GET instead:
    # no-referrer native form POSTs can carry Origin: null and must stay denied.
    token = await read_video_token(request)
    path, _ = checked_video_export(job_id, token)
    return FileResponse(path, media_type="video/mp4", filename="calligraphy_video.mp4", headers=EXPORT_HEADERS)


@app.post("/api/exports/{job_id}/access")
async def access_video_export(job_id: str, request: Request):
    _share_access_limiter.admit(request.client.host if request.client else "unknown")
    token = await read_video_token(request)
    _, expires = checked_video_export(job_id, token)
    return video_access_response(request, "exports", job_id, token, expires, EXPORT_COOKIE_NAME)


@app.api_route("/api/exports/{job_id}/video", methods=["GET", "HEAD"])
def exported_video(job_id: str, request: Request):
    path, _ = checked_video_export(job_id, request.cookies.get(EXPORT_COOKIE_NAME))
    filename = "calligraphy_video.mp4" if request.query_params.get("download") == "1" else None
    return FileResponse(path, media_type="video/mp4", filename=filename, headers=EXPORT_HEADERS)


@app.api_route("/export.html", methods=["GET", "HEAD"])
def video_export_page():
    return FileResponse(Path(__file__).resolve().parent.parent / "frontend" / "export.html", headers={
        **EXPORT_HEADERS, "Content-Security-Policy": SHARE_CSP,
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), autoplay=()",
    })


SHARE_TTL_SECONDS = 72 * 3600
SHARE_COOKIE_NAME = "calligraphy_video_share"
SHARE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
SHARE_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}\Z")
SHARE_UNAVAILABLE = "影片連結無效、已到期或已停用 / Video link unavailable"
SHARE_CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; media-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'"


class ShareAccessLimiter:
    """Bound exchange attempts, never the Range/HEAD requests used for seeking.

    This demo runs exactly one API process. The bounded sliding window stores
    keyed peer digests in memory, not addresses or tokens in persistent logs.
    A multi-process deployment must replace this with a shared edge limiter.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._salt = secrets.token_bytes(32)
        self._peers = {}
        self._all = deque()

    def admit(self, peer):
        key = hashlib.sha256(self._salt + peer.encode()).digest()
        now = time.monotonic()
        with self._lock:
            while self._all and self._all[0] <= now - 60:
                self._all.popleft()
            for identity, attempts in list(self._peers.items()):
                while attempts and attempts[0] <= now - 60:
                    attempts.popleft()
                if not attempts:
                    del self._peers[identity]
            attempts = self._peers.get(key, deque())
            blocked = self._all if len(self._all) >= 600 else attempts if len(attempts) >= 60 else None
            if blocked is not None:
                raise HTTPException(429, "請稍後再試 / Please try again shortly", headers={"Retry-After": str(max(1, math.ceil(blocked[0] + 60 - now)))})
            self._peers.setdefault(key, attempts).append(now)
            self._all.append(now)


_share_access_limiter = ShareAccessLimiter()


def shared_video_path(job, lease_expires=None):
    """A live explicit share lease extends only this video's ordinary retention."""
    try:
        if lease_expires is not None and lease_expires > time.time():
            path, _ = export_video_path(job, lease_expires)
            return path, lease_expires
        # No active lease: creation must not resurrect an already-expired video.
        path, deadline = export_video_path(job)
        if job.get("expires_at"):
            deadline = min(deadline, datetime.fromisoformat(job["expires_at"]).timestamp())
        if deadline <= time.time():
            raise ValueError("expired")
        return path, deadline
    except (HTTPException, OSError, ValueError, TypeError):
        raise HTTPException(404, SHARE_UNAVAILABLE) from None


def checked_video_share(job_id, token):
    if not SHARE_ID.fullmatch(job_id) or not isinstance(token, str) or not SHARE_TOKEN.fullmatch(token):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    db = get_db()
    capability = db.get_video_share(job_id)
    if not capability or capability["expires_at"] <= time.time() or not secrets.compare_digest(
        capability["token_hash"], hashlib.sha256(token.encode("ascii")).hexdigest()
    ):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    path, deadline = shared_video_path(db.get_job(job_id), capability["expires_at"])
    return path, min(capability["expires_at"], deadline)


@app.post("/api/jobs/{job_id}/share-link/status")
async def video_share_status(job_id: str, request: Request):
    """Owner-only read: validate a tab-held bearer without recovering secrets.

    Tokens travel in a bounded body, never a request URL. The database remains
    hash-only and reading/copying cannot rotate a link or renew its lease.
    """
    db = get_db()
    job = db.get_job(job_id) if SHARE_ID.fullmatch(job_id) else None
    if not job or job["session_id"] != request.state.session_id:
        raise HTTPException(404, SHARE_UNAVAILABLE)
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 128:
            raise HTTPException(404, SHARE_UNAVAILABLE)
        body.extend(chunk)
    try:
        data = json.loads(body or b'{}')
        if not isinstance(data, dict) or set(data) - {"token"}:
            raise ValueError()
        token = data.get("token", "")
        if not isinstance(token, str) or (token and not SHARE_TOKEN.fullmatch(token)):
            raise ValueError()
    except (ValueError, UnicodeError):
        raise HTTPException(404, SHARE_UNAVAILABLE) from None
    capability = db.get_video_share(job_id)
    if not capability or capability["expires_at"] <= time.time():
        return JSONResponse({"active": False}, headers=EXPORT_HEADERS)
    shared_video_path(job, capability["expires_at"])
    result = {"active": True, "expires_at": capability["expires_at"]}
    if token and secrets.compare_digest(capability["token_hash"], hashlib.sha256(token.encode("ascii")).hexdigest()):
        result["url"] = f"/watch.html#{job_id}.{token}"
    return JSONResponse(result, headers=EXPORT_HEADERS)


class ShareLinkRequest(BaseModel):
    replace: bool = False


@app.post("/api/jobs/{job_id}/share-link")
def create_video_share(job_id: str, request: Request, options: Optional[ShareLinkRequest] = None):
    db = get_db()
    if not SHARE_ID.fullmatch(job_id):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    token = secrets.token_urlsafe(32)
    expires = time.time() + SHARE_TTL_SECONDS
    def validate(job, previous):
        shared_video_path(job, previous["expires_at"] if previous else None)
        if previous and not (options and options.replace):
            raise HTTPException(409, "已有有效分享連結；請複製原連結，或明確選擇取代。")

    if not db.set_video_share(
        job_id, request.state.session_id, hashlib.sha256(token.encode("ascii")).hexdigest(), expires,
        validate_artifact=validate,
    ):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    return JSONResponse({"url": f"/watch.html#{job_id}.{token}", "expires_at": expires}, headers=EXPORT_HEADERS)


@app.delete("/api/jobs/{job_id}/share-link", status_code=204)
def revoke_video_share(job_id: str, request: Request):
    if not SHARE_ID.fullmatch(job_id) or not get_db().revoke_video_share(job_id, request.state.session_id):
        raise HTTPException(404, SHARE_UNAVAILABLE)
    return Response(status_code=204, headers=EXPORT_HEADERS)


async def read_video_token(request):
    # Fragment bearers belong only in this bounded body, never request URLs.
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
        raise HTTPException(404, SHARE_UNAVAILABLE)
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 128:
            raise HTTPException(404, SHARE_UNAVAILABLE)
        body.extend(chunk)
    try:
        fields = parse_qs(body.decode("ascii"), strict_parsing=True, max_num_fields=1)
        token, = fields["token"]
    except (KeyError, ValueError, UnicodeError):
        raise HTTPException(404, SHARE_UNAVAILABLE) from None
    return token


def video_access_response(request, kind, job_id, token, expires, cookie_name):
    path = f"/api/{kind}/{job_id}"
    response = JSONResponse({"video_url": f"{path}/video", "expires_at": expires}, headers=EXPORT_HEADERS)
    response.set_cookie(
        cookie_name, token, httponly=True, samesite="strict",
        secure=request.url.scheme == "https" or os.environ.get("CALLIGRAPHY_SECURE_COOKIES") == "1",
        path=path, max_age=max(1, math.ceil(expires - time.time())),
        expires=datetime.fromtimestamp(expires, timezone.utc),
    )
    return response


@app.post("/api/shares/{job_id}/access")
async def access_video_share(job_id: str, request: Request):
    # Never accept URL tokens, log request bodies, or fall back to owner cookies.
    _share_access_limiter.admit(request.client.host if request.client else "unknown")
    token = await read_video_token(request)
    _, expires = checked_video_share(job_id, token)
    return video_access_response(request, "shares", job_id, token, expires, SHARE_COOKIE_NAME)


@app.api_route("/api/shares/{job_id}/video", methods=["GET", "HEAD"])
def shared_video(job_id: str, request: Request):
    path, _ = checked_video_share(job_id, request.cookies.get(SHARE_COOKIE_NAME))
    # Query options select disposition only. Authorization is exclusively the
    # per-video cookie and is revalidated before every request, including HEAD.
    filename = "calligraphy_video.mp4" if request.query_params.get("download") == "1" else None
    return FileResponse(path, media_type="video/mp4", filename=filename, headers=EXPORT_HEADERS)


@app.api_route("/watch.html", methods=["GET", "HEAD"])
def video_share_page():
    return FileResponse(Path(__file__).resolve().parent.parent / "frontend" / "watch.html", headers={
        **EXPORT_HEADERS, "Content-Security-Policy": SHARE_CSP,
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), autoplay=()",
    })


# Mount frontend static directory if exists
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
