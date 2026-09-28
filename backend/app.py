"""FastAPI REST API application for Calligraphy Studio."""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Cookie, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from calligraphy.contact_renderer import style_manifest
from calligraphy.font_pipeline import registered_styles
from calligraphy.text.input import parse_text
from .database import Database, get_db
from .worker import execute_job, get_runner

MAX_INPUT_CHARACTERS = 256


class PreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARACTERS)
    style: str = Field(default="kai")


class RenderRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARACTERS)
    style: str = Field(default="kai")
    fps: int = Field(default=24, ge=1, le=60)
    speed: float = Field(default=1.0, ge=0.25, le=4.0)


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
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SESSION_COOKIE_NAME = "calligraphy_session"


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    is_new = False
    if not session_id or len(session_id) > 64:
        session_id = uuid.uuid4().hex
        is_new = True
    request.state.session_id = session_id
    db = get_db()
    db.touch_session(session_id)

    response = await call_next(request)
    if is_new:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=7 * 86400,
        )
    return response


@app.get("/api/styles")
def list_styles():
    """List available writing styles."""
    styles = [
        {"id": "kai", "name": "楷书 (Kai)", "description": "Standard script vector template", "type": "template"},
        {"id": "yan", "name": "颜体 (Yan)", "description": "Yan Zhenqing regular script template", "type": "template"},
    ]
    manifest = style_manifest()
    for name, item in manifest.get("styles", {}).items():
        styles.append({
            "id": name,
            "name": f"{name.capitalize()} (Contact Brush)",
            "description": f"Fixed collection of {item.get('characters', 'preset')} characters",
            "type": "contact",
        })
    for entry in registered_styles():
        styles.append({
            "id": entry["style"],
            "name": entry["style"],
            "description": f"{entry['prepared']} prepared glyphs, extensible font",
            "type": "font",
        })
    return {"styles": styles}


@app.post("/api/previews")
def generate_preview(req: PreviewRequest, request: Request, response: Response):
    """Generate a quick still preview."""
    session_id = request.state.session_id
    try:
        parsed = parse_text(req.text)
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
    job = db.create_job(
        job_id=job_id,
        session_id=session_id,
        job_type="preview",
        text=req.text,
        style=req.style,
        params={},
    )
    # Execute preview immediately for snappy preview response
    success = execute_job(job, db)
    if not success:
        failed_job = db.get_job(job_id)
        raise HTTPException(
            status_code=422,
            detail=failed_job.get("error_message") or "Preview rendering failed",
        )
    return {
        "job_id": job_id,
        "preview_url": f"/api/jobs/{job_id}/image",
    }


@app.post("/api/renders", status_code=status.HTTP_202_ACCEPTED)
def submit_render(req: RenderRequest, request: Request, response: Response):
    """Submit asynchronous video generation job."""
    session_id = request.state.session_id
    try:
        parsed = parse_text(req.text)
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
    job = db.create_job(
        job_id=job_id,
        session_id=session_id,
        job_type="render",
        text=req.text,
        style=req.style,
        params={"fps": req.fps, "speed": req.speed},
    )
    runner = get_runner()
    runner.notify()

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video rendering started",
    }


@app.get("/api/jobs")
def list_session_jobs(request: Request, response: Response):
    """List all jobs for current browser session."""
    session_id = request.state.session_id
    db = get_db()
    jobs = db.list_jobs(session_id)
    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
def get_job_status(job_id: str, request: Request, response: Response):
    """Get status and details of a job."""
    session_id = request.state.session_id
    db = get_db()
    job = db.get_job(job_id)
    if not job or job["session_id"] != session_id:
        raise HTTPException(status_code=404, detail="Job not found")

    download_url = None
    if job["status"] == "succeeded" and job["job_type"] == "render":
        download_url = f"/api/jobs/{job_id}/download"
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
        "download_url": download_url,
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }


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

    return FileResponse(
        str(file_path),
        media_type="image/png",
    )


# Mount frontend static directory if exists
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
