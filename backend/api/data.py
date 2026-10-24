"""
Data layer for the FastAPI backend (api/main.py) — job loading, the
derived location/experience columns, and the resume-scoring state.

DELIBERATELY reuses core/ unchanged: parse_city/parse_country/is_remote,
the matcher's incremental embedding cache, skills, experience extraction.
This module owns NO matching or parsing logic of its own — it is a thin
adapter between SQLite and JSON. Job filtering and matching reuse core/
logic so the React UI receives the same derived fields used by the backend.

STATE: the active resume and scores live in module-level memory. An optional
local saved copy is managed by core/resume_cache.py. This is a single-user tool
running on localhost. It is NOT safe for a multi-user deployment, and
this backend shouldn't be exposed to one without moving this into a real
per-session store.
"""

from functools import wraps
import logging
import sqlite3
import threading
import time
from pathlib import Path

import pandas as pd

import backend.config as config
from backend.core.eligibility import eligibility_evidence
from backend.core.match_sections import eligibility_checks
from backend.core.experience import extract_experience_sentences, extract_min_experience, extract_preferred_experience, experience_requirements
from backend.core.location import is_remote, parse_city, parse_country, is_smartrecruiters_india_location, is_workday_location_placeholder
from backend.core.matcher import embed_jobs_incremental, load_embedding_cache, rank_by_resume, save_embedding_cache, compute_job_pool_key, embed_resume, resume_embedding_key
from backend.core.skills import build_patterns, extract_skills, skill_overlap
from backend.core.storage import get_custom_skills, init_db

from rozgaar.paths import CAREER_DB
DB_PATH = str(CAREER_DB)

# Guards the mutable module state below. FastAPI serves requests from a
# thread pool, so two requests really can touch this concurrently — e.g.
# a dismiss landing while a resume upload is mid-score.
_lock = threading.RLock()
log = logging.getLogger("jobbot.api")

_jobs_cache = {"df": None, "loaded_at": 0.0}
_JOBS_TTL_SECONDS = 30

_embedding_cache = None  # job_id -> (content_hash, tensor), lazily loaded
_initialized_db_paths = set()

# Current resume, if one has been uploaded this run.
_resume = {"key": None, "text": "", "skills": set(), "scores": {}, "explanations": {}, "pool_key": None,
           "filename": None, "embedding": None, "embedding_key": None}


def synchronized(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return wrapped


@synchronized
def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        if str(DB_PATH) not in _initialized_db_paths:
            init_db(conn)
            _initialized_db_paths.add(str(DB_PATH))
    except Exception:
        conn.close()
        raise
    return conn


def _load_jobs_df():
    """Read non-dismissed jobs and add fields needed by the React UI."""
    conn = connect()
    try:
        df = pd.read_sql_query(
            """SELECT jobs.*,
                 EXISTS(SELECT 1 FROM career_export_items WHERE job_id=jobs.id) AS exported
               FROM jobs
               WHERE dismissed = 0
                 AND source NOT GLOB 'reader_*'
                 AND source NOT IN ('unstop', 'linkedin', 'internshala', 'internshala_jobs', 'internshala_internships')
               ORDER BY first_seen DESC""", conn
        )
    finally:
        conn.close()

    if df.empty:
        return df

    # Old Atlassian rows stored iCIMS apply-dialog URLs. Give the UI a
    # usable first-party detail link even before the next collector run.
    atlassian_ids = df["source"].eq("atlassian") & df["id"].str.match(r"^atlassian:\d+$")
    df.loc[atlassian_ids, "url"] = (
        "https://www.atlassian.com/company/careers/details/"
        + df.loc[atlassian_ids, "id"].str.removeprefix("atlassian:")
    )
    df["first_seen"] = pd.to_datetime(df["first_seen"], unit="s")
    df["last_seen"] = pd.to_datetime(df["last_seen"], unit="s")
    df["country"] = df["location"].apply(parse_country)
    # Apply the same country gate to previously saved rows. A corrected
    # location parser should remove foreign postings from the UI immediately,
    # without deleting local history from SQLite.
    df = df[df["country"].isin(["India", "Unknown"]) &
            (~df["source"].eq("workday") | ~df["location"].apply(is_workday_location_placeholder)) &
            (~df["source"].eq("smartrecruiters") | df["location"].apply(is_smartrecruiters_india_location)) &
            (~df["company"].eq("databricks") | df["country"].eq("India"))].copy()
    df["city"] = df["location"].apply(parse_city)
    df["is_remote"] = df["location"].apply(is_remote)
    df["is_ncr"] = df["location"].fillna("").apply(lambda loc: bool(config.LOCATION.search(loc)))
    df["is_india"] = df["country"].isin(["India", "Unknown"])
    df["skills"] = df["skills"].fillna("")
    df["category"] = df["category"].fillna("")
    df["description"] = df["description"].fillna("")
    # Recompute from descriptions so existing rows follow the current policy
    # without changing SQLite or requiring another network collection.
    requirements = [experience_requirements(desc, title) for desc, title in zip(df["description"], df["title"])]
    df["experience_years"] = [required if required is not None else -1 for required, _ in requirements]
    df["preferred_experience_years"] = [preferred if preferred is not None else -1 for _, preferred in requirements]
    return df


def get_jobs_df(force_reload=False):
    """TTL-cached job frame. Invalidated explicitly by dismiss operations
    (see invalidate_jobs) so a removal shows up immediately rather than
    waiting out the TTL."""
    with _lock:
        fresh = (time.time() - _jobs_cache["loaded_at"]) < _JOBS_TTL_SECONDS
        if not force_reload and _jobs_cache["df"] is not None and fresh:
            return _jobs_cache["df"]
        df = _load_jobs_df()
        _jobs_cache["df"] = df
        _jobs_cache["pool_key"] = compute_job_pool_key(df)
        _jobs_cache["loaded_at"] = time.time()
        return df


def invalidate_jobs():
    with _lock:
        _jobs_cache["df"] = None
        _jobs_cache["loaded_at"] = 0.0
        _jobs_cache.pop("pool_key", None)


def _pool_key(df):
    """One fingerprint per cached snapshot; external/test frames are computed directly."""
    if df is _jobs_cache["df"] and "pool_key" in _jobs_cache:
        return _jobs_cache["pool_key"]
    return compute_job_pool_key(df)


def _ensure_embeddings(df):
    """Embeds any job not already covered by the persisted per-job cache.
    Unchanged jobs cost nothing — see core/matcher.py's
    embed_jobs_incremental docstring."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = load_embedding_cache()
    embeddings, updated, num_new = embed_jobs_incremental(df, _embedding_cache)
    if num_new:
        try:
            save_embedding_cache(updated)
        except OSError:
            log.warning("Job embeddings are available in memory, but their cache could not be saved.")
    _embedding_cache = updated
    return embeddings


@synchronized
def rescore(df=None):
    """Recomputes match_pct for the current job pool against the loaded
    resume, storing an {id: pct} map. No-op (and clears any stale scores)
    when no resume is loaded."""
    if not _resume["text"].strip():
        _resume["scores"] = {}
        _resume["explanations"] = {}
        return 0
    df = get_jobs_df() if df is None else df
    if df.empty:
        _resume["scores"] = {}
        _resume["explanations"] = {}
        return 0
    embeddings = _ensure_embeddings(df)
    embedding_key = resume_embedding_key(_resume["text"])
    if (_resume.get("embedding") is None or _resume.get("embedding_key") != embedding_key
            or tuple(_resume["embedding"].shape) != (2, embeddings.shape[-1])):
        _resume["embedding"] = embed_resume(_resume["text"])
        _resume["embedding_key"] = embedding_key
    scored = rank_by_resume(
        df, _resume["text"], job_embeddings=embeddings, resume_skills=_resume["skills"],
        resume_embedding=_resume["embedding"], include_eligibility=False,
    )
    _resume["scores"] = dict(zip(scored["id"], scored["match_pct"]))
    _resume["explanations"] = dict(zip(scored["id"], scored["match_explanation"]))
    _resume["pool_key"] = _pool_key(df)
    return len(_resume["scores"])


@synchronized
def set_resume(key, text, skills, *, filename=None, embedding=None, embedding_key=None):
    previous = dict(_resume)
    _resume["key"] = key
    _resume["text"] = text
    _resume["skills"] = set(skills)
    _resume["filename"] = filename
    if filename is None and key == previous["key"]:
        _resume["filename"] = previous.get("filename")
    if embedding is not None:
        _resume["embedding"], _resume["embedding_key"] = embedding, embedding_key
    try:
        return rescore()
    except Exception:
        _resume.clear()
        _resume.update(previous)
        raise


@synchronized
def clear_resume():
    _resume["key"] = None
    _resume["text"] = ""
    _resume["pool_key"] = None
    _resume["skills"] = set()
    _resume["scores"] = {}
    _resume["explanations"] = {}
    _resume["filename"] = None
    _resume["embedding"] = None
    _resume["embedding_key"] = None


@synchronized
def resume_state():
    return {**_resume, "skills": set(_resume["skills"]), "scores": dict(_resume["scores"]), "explanations": dict(_resume["explanations"])}


def custom_skill_patterns():
    """Built-in SKILLS plus the user's custom keywords."""
    conn = connect()
    try:
        return build_patterns(get_custom_skills(conn))
    finally:
        conn.close()


@synchronized
def job_list_payload(df):
    """Compact per-job rows for the list view. Deliberately EXCLUDES the
    description: descriptions run up to 6,000 chars and a full pool is
    several thousand jobs, which would make this response tens of
    megabytes. The detail endpoint serves description/experience-lines on
    demand instead."""
    if _resume["text"].strip() and _resume.get("pool_key") != _pool_key(df):
        rescore(df)
    scores = _resume["scores"]
    rows = []
    for r in df.itertuples(index=False):
        rows.append({
            "id": r.id,
            "title": r.title,
            "company": r.company,
            "display_company": str(r.company) if r.source.startswith("reader_") else config.DISPLAY_NAMES.get(r.company, str(r.company).title()),
            "location": r.location or "",
            "url": r.url,
            "source": r.source,
            "exported": bool(getattr(r, "exported", False)),
            "source_group": "reader" if r.source.startswith("reader_") else "careers",
            "reader_sources": str(getattr(r, "reader_sources", "") or "").split(",") if getattr(r, "reader_sources", None) else [],
            "description_status": getattr(r, "description_status", "") or "",
            "category": r.category or "",
            "skills": [s for s in (r.skills or "").split(",") if s],
            "experience_years": float(r.experience_years),
            "preferred_experience_years": float(getattr(r, "preferred_experience_years", -1)),
            "description_available": bool(r.description.strip()),
            "first_seen_ms": int(r.first_seen.value // 1000000),
            "first_seen": r.first_seen.strftime("%Y-%m-%d"),
            "last_seen": r.last_seen.strftime("%Y-%m-%d"),
            "is_remote": bool(r.is_remote),
            "is_ncr": bool(r.is_ncr),
            "is_india": bool(r.is_india),
            # Computed HERE, not in the frontend, on purpose:
            # config.EXCLUDE_SENIOR is carefully tuned (Sr./Mgr.
            # abbreviations, trailing level indicators, the fresher-signal
            # suppression) and re-implementing that regex in TypeScript
            # would guarantee the two drift apart.
            "is_senior": bool(config.EXCLUDE_SENIOR.search(r.title or "")),
            "match_pct": scores.get(r.id),
            "match_explanation": _resume["explanations"].get(r.id),
            "tracking_status": getattr(r, "tracking_status", "none"),
            "posting_status": getattr(r, "posting_status", "unknown"),
            "status_evidence": getattr(r, "status_evidence", ""),
        })
    return rows


@synchronized
def job_detail_payload(job_id):
    """Full detail for one job, including the description and the
    experience-relevant lines the UI shows on expand."""
    df = get_jobs_df()
    if df.empty:
        return None
    if _resume["text"].strip() and _resume.get("pool_key") != _pool_key(df):
        rescore(df)
    match = df[df["id"] == job_id]
    if match.empty:
        return None
    row = match.iloc[0]
    description = row["description"] or ""
    job_skills = {s for s in (row["skills"] or "").split(",") if s}
    matched, missing, pct = skill_overlap(_resume["skills"], job_skills)
    explanation = _resume["explanations"].get(job_id)
    if explanation is not None and "eligibility_checks" in explanation:
        explanation = {**explanation, "eligibility_checks": eligibility_checks(
            description, row["location"], _resume["text"], set(explanation.get("missing_required", [])), row["title"])}
    return {
        "id": row["id"],
        "title": row["title"],
        "description": description,
        "match_explanation": explanation,
        "experience_lines": extract_experience_sentences(row["title"] + "\n" + description),
        "eligibility": eligibility_evidence(description, _resume["skills"], row["title"]),
        "skill_match": {
            "matched": sorted(matched),
            "missing": sorted(missing),
            "pct": pct,
        },
    }


def extract_resume_skills(text):
    return extract_skills(text, patterns=custom_skill_patterns())


def tracker_payload(view, limit=100, offset=0):
    """Tracker bypasses relevance/experience filters, so saved jobs remain reachable."""
    clauses = {"saved": "tracking_status = 'saved'", "applied": "tracking_status = 'applied'",
               "removed": "dismissed = 1", "closed": "posting_status = 'closed'", "notes": "notes != ''"}
    clause = clauses[view]
    conn = connect()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM jobs WHERE " + clause).fetchone()[0]
        rows = conn.execute("""SELECT id, title, company, location, url, tracking_status, notes,
            saved_at, applied_at, dismissed, posting_status, status_checked_at, status_evidence,
            last_seen FROM jobs WHERE """ + clause + " ORDER BY first_seen DESC, id LIMIT ? OFFSET ?", (limit, offset))
        jobs = [{**dict(row), "display_company": config.DISPLAY_NAMES.get(row["company"], row["company"].title())} for row in rows]
        return {"jobs": jobs, "total": total}
    finally:
        conn.close()
