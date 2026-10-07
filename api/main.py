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

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import os

from api import data
from core.resume_text import extract_text
from core.runtime import runtime_identity
from core.storage import (
    add_custom_skill, get_custom_skills, get_resume_skill_override,
    mark_dismissed, mark_dismissed_bulk, remove_custom_skill,
    save_resume_skill_override,
)

log = logging.getLogger("jobbot.api")

app = FastAPI(title="Job Intel API")
_RUNTIME = runtime_identity(Path(__file__).resolve().parents[1])
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
    ids: list[str]


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
        mark_dismissed(conn, job_id)
    finally:
        conn.close()
    data.invalidate_jobs()
    return {"dismissed": 1, "id": job_id}


@app.post("/api/resume")
async def upload_resume(file: UploadFile = File(...)):
    name = file.filename or ""
    if Path(name).suffix.lower() not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="upload a PDF, DOCX, or TXT resume")
    max_bytes = 5 * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="resume exceeds the 5 MB limit")
    adapter = _UploadAdapter(name, content)
    resume_key = hashlib.sha256(adapter.read()).hexdigest()
    try:
        text = extract_text(adapter)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"couldn't read resume: {e}")

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="no text could be extracted from that file",
        )

    auto_skills = data.extract_resume_skills(text)
    # A correction saved for this exact resume (by content hash) in an
    # earlier session wins over the raw extraction.
    conn = data.connect()
    try:
        saved = get_resume_skill_override(conn, resume_key)
    finally:
        conn.close()
    effective = saved if saved is not None else auto_skills

    scored = data.set_resume(resume_key, text, effective)
    return {
        "loaded": True,
        "resume_key": resume_key,
        "word_count": len(text.split()),
        "skills": sorted(effective),
        "auto_skills": sorted(auto_skills),
        "had_saved_override": saved is not None,
        "scored": scored,
    }


@app.get("/api/resume")
def get_resume():
    state = data.resume_state()
    return {
        "loaded": bool(state["text"].strip()),
        "resume_key": state["key"],
        "word_count": len(state["text"].split()) if state["text"] else 0,
        "skills": sorted(state["skills"]),
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
    # A new keyword changes what extract_skills() finds in the RESUME
    # immediately; jobs keep their stored skills until
    # `run.py --reprocess-skills` is run.
    state = data.resume_state()
    if added and state["text"].strip():
        data.set_resume(state["key"], state["text"], data.extract_resume_skills(state["text"]))
    return {"added": bool(added), "skills": skills}


@app.delete("/api/custom-skills/{skill}")
def delete_custom_skill(skill: str):
    conn = data.connect()
    try:
        remove_custom_skill(conn, skill)
        skills = sorted(get_custom_skills(conn))
    finally:
        conn.close()
    state = data.resume_state()
    if state["text"].strip():
        data.set_resume(state["key"], state["text"], data.extract_resume_skills(state["text"]))
    return {"skills": skills}


# --- Built React app (optional) --------------------------------------------------
# Mounted only if ui-react/dist exists, so the backend runs fine before the
# frontend has ever been built. When present, the whole app is served from
# this single origin — no CORS, one process, one URL.
_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui-react", "dist")

if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(_DIST, "index.html"))
