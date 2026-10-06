"""
Data layer for the FastAPI backend (api/main.py) — job loading, the
derived location/experience columns, and the resume-scoring state.

DELIBERATELY reuses core/ unchanged: parse_city/parse_country/is_remote,
the matcher's incremental embedding cache, skills, experience extraction.
This module owns NO matching or parsing logic of its own — it is a thin
adapter between SQLite and JSON. Job filtering and matching reuse core/
logic so the React UI receives the same derived fields used by the backend.

STATE: this holds the loaded resume and its scores in module-level
memory. That's deliberate and safe for what this is — a single-user tool
running on localhost. It is NOT safe for a multi-user deployment, and
this backend shouldn't be exposed to one without moving this into a real
per-session store.
"""

import sqlite3
import threading
import time
from pathlib import Path

import pandas as pd

import config
from core.eligibility import eligibility_evidence
from core.experience import extract_experience_sentences, extract_min_experience
from core.location import is_remote, parse_city, parse_country
from core.matcher import (
    embed_jobs_incremental, load_embedding_cache, rank_by_resume,
    save_embedding_cache,
)
from core.skills import build_patterns, extract_skills, skill_overlap
from core.storage import get_custom_skills, init_db

DB_PATH = "db/jobs.db"

# Guards the mutable module state below. FastAPI serves requests from a
# thread pool, so two requests really can touch this concurrently — e.g.
# a dismiss landing while a resume upload is mid-score.
_lock = threading.Lock()

_jobs_cache = {"df": None, "loaded_at": 0.0}
_JOBS_TTL_SECONDS = 30

_embedding_cache = None  # job_id -> (content_hash, tensor), lazily loaded

# Current resume, if one has been uploaded this run.
_resume = {"key": None, "text": "", "skills": set(), "scores": {}, "explanations": {}}


def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn


def _load_jobs_df():
    """Read non-dismissed jobs and add fields needed by the React UI."""
    conn = connect()
    try:
        init_db(conn)  # cheap no-op once migrated; makes a fresh clone work
        df = pd.read_sql_query(
            """SELECT * FROM jobs
               WHERE dismissed = 0
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
    df = df[df["country"].isin(["India", "Unknown"])].copy()
    df["city"] = df["location"].apply(parse_city)
    df["is_remote"] = df["location"].apply(is_remote)
    df["is_ncr"] = df["location"].fillna("").apply(lambda loc: bool(config.LOCATION.search(loc)))
    df["is_india"] = df["country"].isin(["India", "Unknown"])
    df["skills"] = df["skills"].fillna("")
    df["category"] = df["category"].fillna("")
    df["description"] = df["description"].fillna("")
    # Recompute from descriptions so existing rows follow the current policy
    # without changing SQLite or requiring another network collection.
    df["experience_years"] = df["description"].apply(extract_min_experience).astype("Int64").fillna(-1).astype(int)
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
        _jobs_cache["loaded_at"] = time.time()
        return df


def invalidate_jobs():
    with _lock:
        _jobs_cache["df"] = None
        _jobs_cache["loaded_at"] = 0.0


def _ensure_embeddings(df):
    """Embeds any job not already covered by the persisted per-job cache.
    Unchanged jobs cost nothing — see core/matcher.py's
    embed_jobs_incremental docstring."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = load_embedding_cache()
    embeddings, updated, num_new = embed_jobs_incremental(df, _embedding_cache)
    if num_new:
        save_embedding_cache(updated)
    _embedding_cache = updated
    return embeddings


def rescore():
    """Recomputes match_pct for the current job pool against the loaded
    resume, storing an {id: pct} map. No-op (and clears any stale scores)
    when no resume is loaded."""
    if not _resume["text"].strip():
        _resume["scores"] = {}
        _resume["explanations"] = {}
        return 0
    df = get_jobs_df()
    if df.empty:
        _resume["scores"] = {}
        _resume["explanations"] = {}
        return 0
    embeddings = _ensure_embeddings(df)
    scored = rank_by_resume(
        df, _resume["text"], job_embeddings=embeddings, resume_skills=_resume["skills"]
    )
    _resume["scores"] = dict(zip(scored["id"], scored["match_pct"]))
    _resume["explanations"] = dict(zip(scored["id"], scored["match_explanation"]))
    return len(_resume["scores"])


def set_resume(key, text, skills):
    _resume["key"] = key
    _resume["text"] = text
    _resume["skills"] = set(skills)
    return rescore()


def clear_resume():
    _resume["key"] = None
    _resume["text"] = ""
    _resume["skills"] = set()
    _resume["scores"] = {}
    _resume["explanations"] = {}


def resume_state():
    return _resume


def custom_skill_patterns():
    """Built-in SKILLS plus the user's custom keywords."""
    conn = connect()
    try:
        return build_patterns(get_custom_skills(conn))
    finally:
        conn.close()


def job_list_payload(df):
    """Compact per-job rows for the list view. Deliberately EXCLUDES the
    description: descriptions run up to 6,000 chars and a full pool is
    several thousand jobs, which would make this response tens of
    megabytes. The detail endpoint serves description/experience-lines on
    demand instead."""
    scores = _resume["scores"]
    rows = []
    for r in df.itertuples(index=False):
        rows.append({
            "id": r.id,
            "title": r.title,
            "company": r.company,
            "display_company": config.DISPLAY_NAMES.get(r.company, str(r.company).title()),
            "location": r.location or "",
            "url": r.url,
            "source": r.source,
            "category": r.category or "",
            "skills": [s for s in (r.skills or "").split(",") if s],
            "experience_years": int(r.experience_years),
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
        })
    return rows


def job_detail_payload(job_id):
    """Full detail for one job, including the description and the
    experience-relevant lines the UI shows on expand."""
    df = get_jobs_df()
    match = df[df["id"] == job_id]
    if match.empty:
        return None
    row = match.iloc[0]
    description = row["description"] or ""
    job_skills = {s for s in (row["skills"] or "").split(",") if s}
    matched, missing, pct = skill_overlap(_resume["skills"], job_skills)
    return {
        "id": row["id"],
        "title": row["title"],
        "description": description,
        "match_explanation": _resume["explanations"].get(job_id),
        "experience_lines": extract_experience_sentences(description),
        "eligibility": eligibility_evidence(description, _resume["skills"]),
        "skill_match": {
            "matched": sorted(matched),
            "missing": sorted(missing),
            "pct": pct,
        },
    }


def extract_resume_skills(text):
    return extract_skills(text, patterns=custom_skill_patterns())
