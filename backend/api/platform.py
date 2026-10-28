"""Shared-platform controls, mounted beside the existing Rozgaar API."""
from contextlib import asynccontextmanager
import argparse
import secrets
import threading
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.api import data
from backend.core.pipelines import PlatformService
from backend.core.career_exports import create_export, export_payload, remove_export

router = APIRouter(prefix="/api/platform")
_service = None
_lock = threading.Lock()


def get_service():
    global _service
    with _lock:
        if _service is None:
            _service = PlatformService(data.DB_PATH, on_change=data.invalidate_jobs)
        return _service


@asynccontextmanager
async def lifespan(app):
    # Standalone source exports still work without the sibling reader folder.
    # Unit tests substitute DB_PATH and must never import a user's checkpoints.
    from backend.core.reader_bridge import APP_ROOT, READER_ROOT
    from rozgaar.paths import CAREER_DB
    service = None
    if READER_ROOT.is_dir() and str(data.DB_PATH) == str(CAREER_DB):
        service = get_service()
        await run_in_threadpool(service.start)
    try:
        yield
    finally:
        if service:
            await run_in_threadpool(service.close)


def authorize(x_platform_token: str = Header(default=""), service=Depends(get_service)):
    if not secrets.compare_digest(x_platform_token, service.token):
        raise HTTPException(403, "Reload the platform before changing collection settings.")
    return service


@router.get("/state")
def state(service=Depends(get_service)):
    return service.snapshot()


@router.post("/sync")
def sync(service=Depends(authorize)):
    raise HTTPException(410, "The pipelines are separate. Download URL-reader JSON from its own page.")


class CareerExportRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=1000)
    limit: Literal[50, 100, 250, 500, 1000] = 100
    filters: dict[str, str | bool | int | float | None] = Field(default_factory=dict, max_length=20)


@router.post("/career-exports")
def career_export(req: CareerExportRequest, service=Depends(authorize)):
    frame = data.get_jobs_df(force_reload=True)
    selected = frame[frame["id"].isin(req.ids)] if not frame.empty else frame
    summaries = {row["id"]: row for row in data.job_list_payload(selected)} if not selected.empty else {}
    conn = data.connect()
    try:
        payload = create_export(conn, req.ids, summaries, req.filters, req.limit)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    finally:
        conn.close()
    service.changed()
    return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'})


@router.get("/career-exports/{batch_id}")
def download_career_export(batch_id: str):
    conn = data.connect()
    try:
        payload = export_payload(conn, batch_id)
    finally:
        conn.close()
    if payload is None:
        raise HTTPException(404, "JSON batch not found.")
    return JSONResponse(payload, headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'})


@router.post("/career-exports/{batch_id}/remove")
def remove_career_export(batch_id: str, service=Depends(authorize)):
    conn = data.connect()
    try:
        result = remove_export(conn, batch_id)
    except KeyError as exc:
        raise HTTPException(404, "JSON batch not found.") from exc
    finally:
        conn.close()
    service.changed()
    return result


@router.post("/careers/{action}")
def careers(action: str, service=Depends(authorize)):
    try:
        if action == "start":
            service.start_careers()
        elif action == "stop":
            service.stop_careers()
        else:
            raise HTTPException(404, "Unknown collection action.")
        return {"ok": True}
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/reader/state")
def reader_state(file: str | None = None, q: str = Query(default="", max_length=200),
                 page: int = Query(default=1, ge=1), quality: str = "all", service=Depends(get_service)):
    try:
        return service.manager().snapshot(file, q, page, quality)
    except (OSError, ValueError) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/reader/{action}")
def reader_action(action: str, payload: dict, service=Depends(authorize)):
    try:
        manager = service.manager()
        if action == "start":
            import os
            if os.environ.get("JOB_INTEL_OFFLINE") == "1":
                raise ValueError("Offline mode is enabled. Disable it before collecting new jobs.")
            manager.start(payload)
        elif action == "stop":
            manager.stop()
        else:
            raise HTTPException(404, "Unknown reader action.")
        return {"ok": True}
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, TypeError, argparse.ArgumentTypeError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except (OSError, ImportError) as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/reader/job")
def reader_job(file: str, id: str, service=Depends(get_service)):
    try:
        value = service.manager().read_file(file)
        job = next((job for job in value["jobs"] if job.get("job_id") == id), None)
        if job is None:
            raise HTTPException(404, "Item not found.")
        return job
    except (OSError, ValueError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/reader/download")
def reader_download(file: str, service=Depends(get_service)):
    try:
        return JSONResponse(service.manager().read_file(file), headers={"Content-Disposition": f'attachment; filename="{file}"'})
    except (OSError, ValueError) as exc:
        raise HTTPException(404, str(exc)) from exc
