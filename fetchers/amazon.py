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

from fetchers.result import CollectionResult
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


def fetch_query(cfg, deadline=None, max_pages=1000):
    """Read the reported result set; interrupted searches are partial."""
    jobs = []
    seen = set()
    offset = 0
    total = None
    errors = []
    for _ in range(max_pages):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("deadline reached")
            break
        params = {
            "offset": offset, "result_limit": RESULTS_PER_PAGE,
            "sort": "relevant", "loc_query": cfg.get("loc_query", "India"),
            "country": cfg.get("country", "IND"),
        }
        for field in ("industry_experience", "base_query"):
            if cfg.get(field):
                params[field] = cfg[field]
        data = _get(f"{BASE}/en/search.json", params)
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            if offset == 0:
                raise RuntimeError("Amazon: first search page unavailable")
            errors.append(f"page at offset {offset} unavailable")
            break
        reported = data.get("hits")
        if isinstance(reported, int) and reported >= 0:
            total = reported
        else:
            errors.append("reported total missing")
        batch = data["jobs"]
        if not batch:
            break
        fresh = 0
        for raw in batch:
            job = _parse_job(raw)
            key = job["source_id"] or job["url"]
            if job["title"] and key and key not in seen:
                jobs.append(job)
                seen.add(key)
                fresh += 1
        if not fresh:
            errors.append(f"repeated results at offset {offset}")
            break
        offset += len(batch)
        if total is not None and offset >= total:
            break
        time.sleep(0.3)
    else:
        errors.append("pagination safety limit reached")
    if total is not None and len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(dict.fromkeys(errors)))


def collect(configs, deadline=None):
    if not configs:
        return CollectionResult(status="skipped", error="no Amazon searches configured")
    jobs = []
    errors = []
    successes = 0
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = [pool.submit(fetch_query, cfg, deadline) for cfg in configs]
        for future in futures:
            try:
                result = future.result()
                jobs.extend(result)
                successes += 1
                if result.error:
                    errors.append(result.error)
            except Exception as exc:
                errors.append(str(exc))
    if not successes:
        raise RuntimeError("Amazon: all searches failed: " + "; ".join(errors))
    unique = {(job["company"], job["source_id"] or job["url"]): job for job in jobs}
    return CollectionResult(unique.values(), status="partial" if errors else "ok", error="; ".join(errors))
