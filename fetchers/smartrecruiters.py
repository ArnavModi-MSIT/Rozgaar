"""
Fetcher for SmartRecruiters — public, documented, no-auth Posting API.
Docs: https://developers.smartrecruiters.com/docs/posting-api

NOTE: not every SmartRecruiters customer has this public feed enabled (it's
tier-dependent), so a 404/empty result for a real company can mean "this
customer's plan doesn't expose it" rather than "wrong company id."

The list endpoint has no description body — only the per-posting detail
endpoint does. For a company with small total volume (Freshworks/servicenow,
~590 postings combined), this fetcher detail-fetches every posting
unconditionally — well below the scale where the extra HTTP calls cost
meaningfully more time. For a company with real GLOBAL volume (Bosch:
4,824 total postings), config.py's `detail_fetch_india_only` flag gates
the detail-fetch pass to India-only postings.

That gate deliberately does NOT reuse core.location.is_india_or_unknown()
(what Oracle/Workday use) — tried that first, and on Bosch's real data it
only excluded ~48% of postings, because is_india_or_unknown() treats any
country it doesn't recognize by name as "Unknown" and passes it through
(by design, for fetchers that only ever get free-text location strings
to parse). Bosch posts across dozens of countries well beyond that
short list (a live sample included Romania, which fell through to
"Unknown" and would've been detail-fetched for nothing). SmartRecruiters'
own API already returns a clean 2-letter ISO country code per posting
(`location.country`, e.g. "in"/"de"/"ro") — exact structured data, not a
free-text guess — so the gate filters on that directly instead, via each
job's internal `_country_code` field (same pattern as fetchers/workday.py's
`_ext_path`: carried through fetch_smartrecruiters() for collect() to use,
stripped before any job dict is returned — never written to the db).
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
    parts = [loc.get("city", ""), loc.get("region", ""), loc.get("country", "")]
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
    """configs: list of {"company_id": ..., "detail_fetch_india_only": bool
    (optional, default False)} dicts — see config.py's SMARTRECRUITERS."""
    if not configs:
        return []
    jobs = []
    jobs_by_company = {}  # company_id -> (jobs, detail_fetch_india_only)
    failures = 0
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = {pool.submit(fetch_smartrecruiters, cfg["company_id"], deadline): cfg for cfg in configs}
        for f in futures:
            cfg = futures[f]
            try:
                company_jobs = f.result()
                jobs += company_jobs
                jobs_by_company[cfg["company_id"]] = (company_jobs, cfg.get("detail_fetch_india_only", False))
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
    for company_jobs, india_only in jobs_by_company.values():
        if india_only:
            # Empty country code (missing from the API response) counts as
            # "keep it" not "exclude it" — same never-drop-on-unparseable
            # rule every other fetcher's India-scoping already follows,
            # just applied to a missing structured field instead of an
            # unparseable free-text string.
            to_enrich = [j for j in company_jobs if j["_country_code"] in ("", "in")]
        else:
            to_enrich = company_jobs
        _enrich_company_jobs(to_enrich)

    # _country_code was only ever needed for the gate above — strip it so
    # every returned job dict matches the documented schema, same reasoning
    # as fetchers/workday.py's _ext_path cleanup.
    for job in jobs:
        job.pop("_country_code", None)

    return jobs
