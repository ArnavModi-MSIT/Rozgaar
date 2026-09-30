"""
Fetcher for Amazon Jobs (amazon.jobs) — confirmed via debug/debug_amazon.py:
the public search page itself has no job data in its raw HTML (React SPA
shell), but a JSON variant of the same search URL (amazon.jobs/en/search.json,
same query params) returns complete structured data directly — full
description, basic/preferred qualifications, clean pre-normalized location.
No HTML scraping needed, no bot-blocking encountered.

Confirmed real response fields: title, company_name, description,
basic_qualifications, preferred_qualifications, normalized_location,
job_path (relative URL), id_icims (clean numeric id) / id (uuid fallback).
Response also has a top-level "hits" (total count) alongside "jobs" (this
page's results) — standard offset/result_limit pagination.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from fetchers.http_client import get_json
from fetchers.standard import strip_html

log = logging.getLogger("jobbot")

BASE = "https://www.amazon.jobs"
RESULTS_PER_PAGE = 50

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})


def _get(url, params):
    return get_json(SESSION, url, params=params)


def _parse_job(j):
    parts = []
    if j.get("description"):
        parts.append(j["description"])
    if j.get("basic_qualifications"):
        parts.append(f"Basic Qualifications:\n{j['basic_qualifications']}")
    if j.get("preferred_qualifications"):
        parts.append(f"Preferred Qualifications:\n{j['preferred_qualifications']}")
    combined = "\n\n".join(parts)

    job_path = j.get("job_path", "")
    url = f"{BASE}{job_path}" if job_path else ""

    source_id = j.get("id_icims") or j.get("id", "")

    return {
        "company": j.get("company_name") or "Amazon",
        "source_id": str(source_id),
        "title": j.get("title", ""),
        "location": j.get("normalized_location") or j.get("location", ""),
        "url": url,
        "description": strip_html(combined, max_chars=None)[:6000] if combined else "",
    }


def fetch_query(cfg, deadline=None, max_pages=10):
    """cfg controls the search: loc_query/country scope location,
    industry_experience/base_query narrow further (e.g.
    industry_experience="less_than_1_year" for fresher/intern-level roles,
    matching this project's original real Amazon URL). max_pages caps
    pagination — Amazon's India job count can be large, this keeps a
    single query bounded."""
    jobs = []
    offset = 0
    result_limit = RESULTS_PER_PAGE
    while offset // result_limit < max_pages:
        if deadline is not None and time.monotonic() >= deadline:
            break
        params = {
            "offset": offset,
            "result_limit": result_limit,
            "sort": "relevant",
            "loc_query": cfg.get("loc_query", "India"),
            "country": cfg.get("country", "IND"),
        }
        if cfg.get("industry_experience"):
            params["industry_experience"] = cfg["industry_experience"]
        if cfg.get("base_query"):
            params["base_query"] = cfg["base_query"]

        data = _get(f"{BASE}/en/search.json", params)
        if not data:
            break
        page_jobs = data.get("jobs", [])
        # hits defaulting to 0 (found via review, same failure class as
        # fetchers/icims.py and fetchers/oracle.py) would make
        # "offset >= total" trivially true after just page one if this
        # field were ever missing or zero. "not page_jobs" (page came
        # back empty) is the real stop signal; only trust the total-based
        # check when a real (truthy) total came back.
        total = data.get("hits", 0)
        if not page_jobs:
            break
        for j in page_jobs:
            job = _parse_job(j)
            if job["title"]:
                jobs.append(job)
        offset += result_limit
        if total and offset >= total:
            break
        time.sleep(0.3)
    return jobs


def collect(configs, deadline=None):
    # Parallelized across configs — was fully sequential before. Same
    # pattern as fetchers/oracle.py's collect(); pagination within a
    # single config still runs sequentially inside fetch_query().
    if not configs:
        return []
    jobs = []
    failures = 0
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = [pool.submit(fetch_query, cfg, deadline) for cfg in configs]
        for f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("amazon query failed: %s", e)
                failures += 1
    if failures == len(configs):
        raise RuntimeError(f"amazon fetcher: all {len(configs)} quer(ies) failed")
    return jobs
