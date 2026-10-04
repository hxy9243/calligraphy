import json
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
from pydantic import BaseModel, Field, field_validator

from calligraphy.font_pipeline import registered_styles
from calligraphy.text.converter import ConversionUnavailableError, convert_text
from calligraphy.text.input import parse_text
from .database import Database, get_db
from .style_catalog import STYLE_ALIASES
from .worker import execute_job, get_runner

MAX_INPUT_CHARACTERS = 256
MAX_LINE_CHARACTERS = 20

class ConvertRequest(BaseModel):
    text: str
    target: Literal["simp", "trad", "zh-hans", "zh-hant"] = "trad"


class PreviewRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARACTERS)
    style: str = Field(default="kai")
    direction: Literal["vertical-rl", "horizontal-lr"] = "vertical-rl"
    format: str = Field(default="auto")
    spacing: float = Field(default=0.18, ge=0.0, le=2.0)
    punctuation: str = Field(default="omit")
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)

    @field_validator("text")
    @classmethod
    def validate_line_length(cls, v: str) -> str:
        for idx, line in enumerate(v.split("\n"), 1):
            if len(line) > MAX_LINE_CHARACTERS:
                raise ValueError(
                    f"第 {idx} 行超出单行 {MAX_LINE_CHARACTERS} 字限制（当前 {len(line)} 字），请换行后再试 / Line {idx} exceeds {MAX_LINE_CHARACTERS}-character limit ({len(line)} chars)."
                )
        return v


class RenderRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_INPUT_CHARACTERS)
    style: str = Field(default="kai")
    direction: Literal["vertical-rl", "horizontal-lr"] = "vertical-rl"
    fps: int = Field(default=24, ge=1, le=60)
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    spacing: float = Field(default=0.18, ge=0.0, le=2.0)
    punctuation: str = Field(default="omit")
    width: Optional[int] = Field(default=None)
    height: Optional[int] = Field(default=None)

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
    }
    for entry in registered_styles():
        display_name = font_names.get(entry["style"], entry["style"])
        styles.append({
            "id": entry["style"],
            "name": display_name,
            "description": f"{entry['prepared']} prepared glyphs, extensible font",
            "type": "font",
        })
    return {"styles": styles}


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
    """Retrieve full calligraphy font database catalog."""
    catalog_path = Path(__file__).resolve().parent.parent / "data" / "calligraphy_fonts.json"
    if catalog_path.exists():
        with open(catalog_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content=[])


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
    chosen_style = STYLE_ALIASES.get(req.style, req.style)
    params = {
        "format": req.format,
        "spacing": req.spacing,
        "direction": req.direction,
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
    }


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
    chosen_style = STYLE_ALIASES.get(req.style, req.style)
    params = {
        "fps": req.fps,
        "speed": req.speed,
        "spacing": req.spacing,
        "direction": req.direction,
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
    )
    runner = get_runner()
    runner.notify()

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "message": "Video render accepted",
    }


@app.get("/api/jobs")
def list_session_jobs(request: Request, response: Response):
    """List all jobs for current browser session."""
    session_id = request.state.session_id
    db = get_db()
    jobs = db.list_jobs(session_id)
    for j in jobs:
        if j.get("status") == "succeeded" and j.get("job_type") == "render":
            j["download_url"] = f"/api/jobs/{j['job_id']}/download"
            j["video_url"] = f"/api/jobs/{j['job_id']}/video"
        elif j.get("status") == "succeeded" and j.get("job_type") == "preview":
            j["download_url"] = f"/api/jobs/{j['job_id']}/image"
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
        "download_url": download_url,
        "video_url": video_url,
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
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


# Mount fonts static directory if exists
fonts_dir = Path(__file__).resolve().parent.parent / "data" / "fonts"
if fonts_dir.exists():
    app.mount("/fonts", StaticFiles(directory=str(fonts_dir)), name="fonts")

# Mount frontend static directory if exists
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
