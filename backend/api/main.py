"""
FastAPI backend for the React UI (ui-react/). It reads db/jobs.db and
uses core/ for resume parsing, matching, and job display data.

Run:
  .venv/Scripts/python.exe -m uvicorn api.main:app --reload --port 8000

Endpoints (all JSON unless noted):
  GET    /api/stats                    counts for the header tiles
  GET    /api/jobs                     every non-dismissed job, list-shaped
  GET    /api/jobs/{id}                one job + description/experience lines
  POST   /api/jobs/{id}/dismiss        remove a single job
  POST   /api/jobs/dismiss-bulk        remove many at once
  POST   /api/resume                   multipart upload -> parse -> score
  GET    /api/resume                   what's currently loaded
  DELETE /api/resume                   unload it
  POST   /api/resume/previous          use the locally saved resume
  DELETE /api/resume/saved             delete the saved copy
  PUT    /api/resume/skills            correct the extracted skills + rescore
  GET    /api/custom-skills            user-added skill keywords
  POST   /api/custom-skills            add one
  DELETE /api/custom-skills/{skill}    remove one

Filtering is done in the React UI. /api/jobs returns the visible pool,
then the client applies location and experience filters in memory.
"""

import hashlib
import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

import os

from backend.api import data
from backend.core.resume_text import extract_text
from backend.core import resume_cache
from backend.core.runtime import runtime_identity
from backend.core.storage import add_custom_skill, get_custom_skills, get_resume_skill_override, mark_dismissed, mark_dismissed_bulk, remove_custom_skill, save_resume_skill_override, restore_jobs, update_job_state
from backend.core.source_health import dashboard
from backend.api.platform import router as platform_router, lifespan as platform_lifespan

log = logging.getLogger("jobbot.api")

app = FastAPI(title="Job Intel API", lifespan=platform_lifespan)
app.include_router(platform_router)
from raambaad.paths import ROOT, FRONTEND
_RUNTIME = runtime_identity(ROOT)
_LOCAL_ORIGINS = {
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (8000, 5173, 4173)
}


@app.middleware("http")
async def protect_local_mutations(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in _LOCAL_ORIGINS:
        return JSONResponse({"detail": "Changes are only allowed from the local Job Intel UI."}, status_code=403)
    return await call_next(request)


@app.get("/api/runtime")
def get_runtime():
    """Launcher diagnostic: identity captured when this backend was imported."""
    return _RUNTIME

# The Vite dev server runs on its own origin during development. Once the
# React app is built, main.py serves it from THIS origin (see the static
# mount at the bottom) and CORS stops mattering — but the dev loop needs
# it. Localhost-only: this backend reads a local SQLite file and is not
# meant to be exposed beyond the machine it runs on.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DismissBulkRequest(BaseModel):
    ids: list[str] = Field(max_length=10000)


class JobStateRequest(BaseModel):
    tracking_status: Literal["none", "saved", "applied"] | None = None
    notes: str | None = Field(default=None, max_length=4000)
    posting_status: Literal["open", "closed", "unknown"] | None = None


class ResumeSkillsRequest(BaseModel):
    skills: list[str]


class CustomSkillRequest(BaseModel):
    skill: str


class _UploadAdapter:
    """Adapt FastAPI UploadFile to the file-like interface extract_text expects."""

    def __init__(self, name: str, content: bytes):
        self.name = name
        self._data = content

    def seek(self, pos):
        return None  # already fully read into memory

    def read(self):
        return self._data


@app.get("/api/stats")
def get_stats():
    df = data.get_jobs_df()
    return {
        "visible": int(len(df)),
        "companies": int(df["company"].nunique()) if not df.empty else 0,
        "resume_loaded": bool(data.resume_state()["text"].strip()),
    }


@app.get("/api/jobs")
def get_jobs():
    df = data.get_jobs_df()
    if df.empty:
        return {"jobs": []}
    return {"jobs": data.job_list_payload(df)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    detail = data.job_detail_payload(job_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="job not found")
    return detail


@app.get("/api/source-health")
def source_health():
    conn = data.connect()
    try:
        return dashboard(conn)
    finally:
        conn.close()


@app.get("/api/tracker")
def tracker(view: Literal["saved", "applied", "removed", "closed", "notes"] = "saved",
            limit: int = 100, offset: int = 0):
    return data.tracker_payload(view, min(200, max(1, limit)), max(0, offset))


@app.put("/api/jobs/{job_id}/state")
def job_state(job_id: str, req: JobStateRequest):
    conn = data.connect()
    try:
        found = update_job_state(conn, job_id, **req.model_dump())
    finally:
        conn.close()
    if not found:
        raise HTTPException(status_code=404, detail="job not found")
    data.invalidate_jobs()
    return {"id": job_id, "updated": True}


@app.post("/api/restore")
def restore(req: DismissBulkRequest):
    conn = data.connect()
    try:
        count = restore_jobs(conn, req.ids)
    finally:
        conn.close()
    data.invalidate_jobs()
    return {"restored": count}


@app.post("/api/jobs/dismiss-bulk")
def dismiss_bulk(req: DismissBulkRequest):
    if not req.ids:
        return {"dismissed": 0}
    conn = data.connect()
    try:
        count = mark_dismissed_bulk(conn, req.ids)
    finally:
        conn.close()
    data.invalidate_jobs()
    return {"dismissed": count}


@app.post("/api/jobs/{job_id}/dismiss")
def dismiss_job(job_id: str):
    conn = data.connect()
    try:
        count = mark_dismissed(conn, job_id)
    finally:
        conn.close()
    data.invalidate_jobs()
    if not count:
        raise HTTPException(status_code=404, detail="job not found")
    return {"dismissed": count, "id": job_id}


@data.synchronized
def _activate_resume(name=None, content=None, *, previous=None, save_for_later=False):
    cached = previous if previous is not None else resume_cache.load()
    parser_signature = resume_cache.parser_signature()
    resume_key = hashlib.sha256(content).hexdigest() if content is not None else cached["resume_key"]
    reuse_text = bool(cached and cached["resume_key"] == resume_key and
                     (content is None or cached.get("parser_signature") == parser_signature))
    if reuse_text:
        text = cached["text"]
        parser_signature = cached.get("parser_signature", "")
        name = name or cached["filename"]
    else:
        try:
            text = extract_text(_UploadAdapter(name, content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"couldn't read resume: {e}")
    if not text.strip():
        raise HTTPException(status_code=400, detail="no text could be extracted from that file")
    patterns = data.custom_skill_patterns()
    signature = hashlib.sha256(repr(sorted((skill, pattern.pattern, pattern.flags)
                                          for skill, pattern in patterns.items())).encode()).hexdigest()
    auto_skills = (set(cached["auto_skills"]) if reuse_text and cached.get("skills_signature") == signature
                   else data.extract_resume_skills(text))
    # A correction saved for this exact resume (by content hash) in an
    # earlier session wins over the raw extraction.
    conn = data.connect()
    try:
        saved = get_resume_skill_override(conn, resume_key)
    finally:
        conn.close()
    effective = saved if saved is not None else auto_skills

    embedding = cached.get("embedding") if reuse_text else None
    embedding_key = cached.get("embedding_key") if reuse_text else None
    scored = data.set_resume(resume_key, text, effective, filename=name,
                             embedding=embedding, embedding_key=embedding_key)
    state = data.resume_state()
    save_warning = None
    if save_for_later:
        try:
            resume_cache.save({"resume_key": resume_key, "filename": name, "text": text,
                               "auto_skills": sorted(auto_skills), "skills_signature": signature,
                               "parser_signature": parser_signature, "embedding": state.get("embedding"),
                               "embedding_key": state.get("embedding_key")})
        except OSError:
            log.warning("Could not save the local resume cache", exc_info=True)
            save_warning = "Resume loaded, but the saved copy could not be written. Check free disk space and folder permissions."
    return {
        "loaded": True,
        "resume_key": resume_key,
        "word_count": len(text.split()),
        "skills": sorted(effective),
        "auto_skills": sorted(auto_skills),
        "had_saved_override": saved is not None,
        "scored": scored,
        "filename": name,
        "saved_resume": resume_cache.info(),
        "reused_text": reuse_text,
        "reused_embedding": scored > 0 and embedding is not None and state.get("embedding") is embedding,
        "save_warning": save_warning,
    }


@app.post("/api/resume")
async def upload_resume(file: UploadFile = File(...), save_for_later: bool = Form(False)):
    name = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if Path(name).suffix.lower() not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="upload a PDF, DOCX, or TXT resume")
    max_bytes = 5 * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="resume exceeds the 5 MB limit")
    return await run_in_threadpool(_activate_resume, name, content, save_for_later=save_for_later)


@app.post("/api/resume/previous")
@data.synchronized
def use_previous_resume():
    cached = resume_cache.load()
    if cached is None:
        raise HTTPException(status_code=404, detail="No saved resume available. Upload a resume and select Save for next time.")
    return _activate_resume(previous=cached, save_for_later=True)


@app.delete("/api/resume/saved")
@data.synchronized
def delete_saved_resume():
    resume_cache.delete()
    return {"saved_resume": None}


@app.get("/api/resume")
def get_resume():
    state = data.resume_state()
    return {
        "loaded": bool(state["text"].strip()),
        "resume_key": state["key"],
        "word_count": len(state["text"].split()) if state["text"] else 0,
        "skills": sorted(state["skills"]),
        "filename": state.get("filename"),
        "saved_resume": resume_cache.info(),
    }


@app.delete("/api/resume")
def delete_resume():
    data.clear_resume()
    return {"loaded": False}


@app.put("/api/resume/skills")
def update_resume_skills(req: ResumeSkillsRequest):
    state = data.resume_state()
    if not state["text"].strip():
        raise HTTPException(status_code=400, detail="no resume loaded")
    skills = {s.strip().lower() for s in req.skills if s.strip()}
    conn = data.connect()
    try:
        save_resume_skill_override(conn, state["key"], skills)
    finally:
        conn.close()
    scored = data.set_resume(state["key"], state["text"], skills)
    return {"skills": sorted(skills), "scored": scored}


@app.get("/api/custom-skills")
def list_custom_skills():
    conn = data.connect()
    try:
        return {"skills": sorted(get_custom_skills(conn))}
    finally:
        conn.close()


@app.post("/api/custom-skills")
def create_custom_skill(req: CustomSkillRequest):
    conn = data.connect()
    try:
        added = add_custom_skill(conn, req.skill)
        skills = sorted(get_custom_skills(conn))
    finally:
        conn.close()
    if added:
        _refresh_resume_skills()
    return {"added": bool(added), "skills": skills}


@data.synchronized
def _refresh_resume_skills():
    """Global vocabulary edits respect the user's full-set correction, even empty."""
    state = data.resume_state()
    if not state["text"].strip():
        return
    conn = data.connect()
    try:
        saved = get_resume_skill_override(conn, state["key"])
    finally:
        conn.close()
    effective = saved if saved is not None else data.extract_resume_skills(state["text"])
    data.set_resume(state["key"], state["text"], effective)


@app.delete("/api/custom-skills/{skill}")
def delete_custom_skill(skill: str):
    conn = data.connect()
    try:
        removed = remove_custom_skill(conn, skill)
        skills = sorted(get_custom_skills(conn))
    finally:
        conn.close()
    if removed:
        _refresh_resume_skills()
    return {"skills": skills}


# --- Built React app (optional) --------------------------------------------------
# Mounted only if ui-react/dist exists, so the backend runs fine before the
# frontend has ever been built. When present, the whole app is served from
# this single origin — no CORS, one process, one URL.
_DIST = str(FRONTEND / "dist")

if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(_DIST, "index.html"))
