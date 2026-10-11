"""
Fetcher for SmartRecruiters — public, documented, no-auth Posting API.
Docs: https://developers.smartrecruiters.com/docs/posting-api

All returned postings must have explicit location.country=IN. Global listing
pagination is still read, but foreign/missing country records are excluded before
enrichment and storage. Saved legacy records are also guarded in the API.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from fetchers.http_client import get_json
from fetchers.standard import strip_html

log = logging.getLogger("jobbot")
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "jobbot/1.0"

BASE = "https://api.smartrecruiters.com/v1/companies"


def _get(url):
    return get_json(SESSION, url)


def _format_location(loc):
    if not loc:
        return ""
    country = loc.get("country", "")
    if country.lower() == "in":
        country = "India"
    parts = [loc.get("city", ""), loc.get("region", ""), country]
    text = ", ".join(p for p in parts if p)
    if loc.get("remote"):
        text = f"{text} (Remote)" if text else "Remote"
    return text


def fetch_posting_description(company_id, posting_id):
    """Full job description via the per-posting detail endpoint. Response
    shape: {"jobAd": {"sections": {"jobDescription": {"text": "<html>"},
    "qualifications": {...}, "additionalInformation": {...}}}}. Each
    section's HTML (which itself may contain nested subsections like
    Required/Preferred/Key Competencies within "qualifications" — that's
    all part of the same text blob, not separate API fields) is stripped
    and joined into one plain-text description."""
    data = _get(f"{BASE}/{company_id}/postings/{posting_id}")
    if not data:
        return ""
    sections = (data.get("jobAd") or {}).get("sections") or {}
    texts = []
    for key in ("jobDescription", "qualifications", "additionalInformation"):
        html = (sections.get(key) or {}).get("text", "")
        if html:
            texts.append(html)
    if not texts:
        return ""
    return strip_html(" ".join(texts), max_chars=None)[:6000]


def fetch_smartrecruiters(company_id, deadline=None):
    """deadline: an optional time.monotonic() timestamp — pagination stops
    once past it, returning whatever's been collected so far. Same
    pattern as fetchers/oracle.py / fetchers/workday.py."""
    jobs = []
    offset = 0
    limit = 100
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break
        data = _get(f"{BASE}/{company_id}/postings?limit={limit}&offset={offset}")
        if not data:
            break
        content = data.get("content", [])
        # totalFound defaulting to 0 (via .get's fallback) used to make
        # "offset >= total" trivially true after just page one — same
        # failure class found and fixed in fetchers/icims.py,
        # fetchers/oracle.py, and fetchers/amazon.py. Only trust the
        # total-based stop condition when a real (truthy) total came
        # back; "not content" (page came back empty) is the reliable
        # fallback signal.
        total = data.get("totalFound", 0)
        if not content:
            break
        for j in content:
            posting_id = j.get("id", "")
            loc = j.get("location") or {}
            jobs.append({
                "company": company_id,
                "source_id": str(posting_id),
                "title": j.get("name", ""),
                "location": _format_location(loc),
                "url": f"https://jobs.smartrecruiters.com/{company_id}/{posting_id}",
                # List endpoint has no description body — filled in below
                # for every posting (see module docstring).
                "description": "",
                # Internal only, used by collect()'s detail_fetch_india_only
                # gate — never written to the database (save_job() only
                # pulls the specific keys it knows about) and stripped
                # before any job dict is returned below, same as
                # fetchers/workday.py's _ext_path.
                "_country_code": (loc.get("country") or "").strip().lower(),
            })
        offset += limit
        if len(content) < limit or (total and offset >= total):
            break
    return jobs


def _enrich(job):
    desc = fetch_posting_description(job["company"], job["source_id"])
    if desc:
        job["description"] = desc
    return job


def _enrich_company_jobs(jobs, probe_size=10, failure_threshold=0.8):
    """Enrich a single company's jobs, but bail early if the detail
    endpoint looks broadly broken for that company (e.g. its plan later
    disabled the endpoint, or it started 404/403-ing consistently) —
    a small probe batch decides whether it's worth continuing before
    committing to hundreds of doomed requests. Scoped per-company since
    one company's endpoint being down says nothing about another's."""
    if not jobs:
        return
    probe, rest = jobs[:probe_size], jobs[probe_size:]

    # 5, not 8 — reduced after review: a company with hundreds of jobs
    # means this detail-fetch pass is a real concurrent burst against a
    # single host (api.smartrecruiters.com), which is exactly the kind of
    # pattern likely to trigger a 429. Now that 429s are actually retried
    # with backoff (see fetchers/http_client.py) rather than treated as a
    # permanent failure, a lower concurrency ceiling also means less
    # total backoff time paid if the endpoint does start rate-limiting.
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_enrich, j): j for j in probe}
        failures = 0
        for f in futures:
            job = futures[f]
            try:
                f.result()
                if not job["description"]:
                    failures += 1
            except Exception:
                failures += 1

    if probe and failures / len(probe) >= failure_threshold:
        log.warning(
            "smartrecruiters %s: detail endpoint looks broken (%d/%d probe failures) — "
            "skipping remaining %d job(s), titles stay description-less this run",
            probe[0]["company"], failures, len(probe), len(rest),
        )
        return

    if rest:
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_enrich, j) for j in rest]
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    log.exception("smartrecruiters detail fetch failed: %s", e)


def collect(configs, deadline=None):
    """Collect configured company boards, returning explicit India postings only."""
    if not configs:
        return []
    jobs = []
    jobs_by_company = {}  # company_id -> India-only jobs
    failures = 0
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = {pool.submit(fetch_smartrecruiters, cfg["company_id"], deadline): cfg for cfg in configs}
        for f in futures:
            cfg = futures[f]
            try:
                company_jobs = f.result()
                company_jobs = [j for j in company_jobs if j.get("_country_code") == "in"]
                jobs += company_jobs
                jobs_by_company[cfg["company_id"]] = company_jobs
            except Exception as e:
                log.exception("a smartrecruiters company fetch failed: %s", e)
                failures += 1

    if failures == len(configs):
        # Every configured company errored, not just returned zero
        # postings — surface this so run.py records status="failed"
        # instead of an indistinguishable "0 jobs, ok".
        raise RuntimeError(f"smartrecruiters fetcher: all {len(configs)} company fetch(es) failed")

    # Enriched per-company (not one big batch across all companies) so the
    # circuit breaker above can judge each company's endpoint health
    # independently — company count here is small, so the lost cross-
    # company concurrency is negligible.
    for company_jobs in jobs_by_company.values():
        _enrich_company_jobs(company_jobs)

    # _country_code was only ever needed for the gate above — strip it so
    # every returned job dict matches the documented schema, same reasoning
    # as fetchers/workday.py's _ext_path cleanup.
    for job in jobs:
        job.pop("_country_code", None)

    return jobs
