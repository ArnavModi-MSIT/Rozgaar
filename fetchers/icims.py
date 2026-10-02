"""
Fetcher for iCIMS/Jibe-powered career sites (recognizable by *.jibecdn.com
assets, cdn*.icims.com requests, and a same-origin JSON jobs endpoint).

Two deployment variants confirmed so far:
- ZS Associates (jobs.zs.com): endpoint at /jobs?page=N, jobs nested under
  a "data" key, detail links on a separate apply_domain
  (careers-zs.icims.com). The current ZS /api/jobs endpoint is handled by fetchers/zs.py.
- Cvent (careers.cvent.com): endpoint at /api/jobs?page=N (confirmed via
  debug/debug_cvent.py — 200, real JSON, full description field in the
  list response), job objects flat (no "data" wrapper), detail URL is
  slug-based on the SAME domain: https://careers.cvent.com/jobs/{slug}.
  Also honors server-side filters in the query string (e.g.
  locations=Gurugram,,India cut 117 global postings to 43).

cfg keys:
  company        required
  jobs_domain    required — host serving the JSON
  api_path       optional, default "/jobs" (ZS-style); use "/api/jobs" for Cvent-style
  extra_params   optional query-string suffix, e.g. "locations=Gurugram,,India"
  apply_domain   optional — if set, job URL = https://{apply_domain}/jobs/{req_id}
                 (ZS-style); if absent, https://{jobs_domain}/jobs/{slug}
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from fetchers.http_client import get_json
from .standard import strip_html  # reuse the same HTML->text helper

log = logging.getLogger("jobbot")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",  # without this some deployments
    # serve the Angular app shell (HTML) instead of JSON — confirmed via
    # debug_icims.py on ZS.
})


def _fetch_page(jobs_domain, page, api_path="/jobs", extra_params=""):
    url = f"https://{jobs_domain}{api_path}?page={page}"
    if extra_params:
        url += f"&{extra_params}"
    headers = {"Referer": f"https://{jobs_domain}/jobs"}
    return get_json(SESSION, url, headers=headers)


def fetch_icims(cfg, deadline=None):
    """deadline: an optional time.monotonic() timestamp — pagination stops
    once past it, returning whatever's been collected so far. Same pattern
    as fetchers/oracle.py / fetchers/workday.py / fetchers/phenom.py — a
    company with an unexpectedly large posting count could otherwise run
    past the outer run() time budget with nothing to interrupt it."""
    jobs_domain = cfg["jobs_domain"]
    api_path = cfg.get("api_path", "/jobs")
    extra_params = cfg.get("extra_params", "")
    apply_domain = cfg.get("apply_domain")
    jobs = []
    page = 1
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break
        data = _fetch_page(jobs_domain, page, api_path, extra_params)
        if not data:
            break
        page_jobs = data.get("jobs", [])
        # totalCount defaulting to 0 (via .get's fallback) used to make
        # "if len(jobs) >= total: break" trivially true after just page
        # one for any deployment that omits or zeroes this field — the
        # same failure class fetchers/workday.py already had to guard
        # against. Only trust the total-based stop condition when a real
        # (truthy) total was actually returned; otherwise rely on the
        # "page came back empty" check below to know when to stop.
        total = data.get("totalCount", 0)
        if not page_jobs:
            break
        for j in page_jobs:
            # ZS-style nests fields under "data"; Cvent-style is flat.
            d = j.get("data", j) if isinstance(j, dict) else {}
            req_id = d.get("req_id") or d.get("slug", "")
            slug = d.get("slug", "")
            loc_parts = [d.get("location_name", ""), d.get("city", ""),
                         d.get("state", ""), d.get("country", "")]
            # Cvent's location_name already reads "Gurugram, India" while
            # city/country repeat the same info — dedupe while keeping order.
            seen = set()
            parts = []
            for p in loc_parts:
                for token in [t.strip() for t in p.split(",") if t.strip()]:
                    if token.lower() not in seen:
                        seen.add(token.lower())
                        parts.append(token)
            location = ", ".join(parts)
            if apply_domain:
                url = f"https://{apply_domain}/jobs/{req_id}"
            else:
                url = f"https://{jobs_domain}/jobs/{slug or req_id}"
            jobs.append({
                "company": cfg["company"],
                "source_id": str(req_id),
                "title": d.get("title", ""),
                "location": location,
                "url": url,
                "description": strip_html(d.get("description", ""), max_chars=None)[:6000],
            })
        page += 1
        if total and len(jobs) >= total:
            break
        time.sleep(0.3)
    return jobs


def collect(icims_configs, deadline=None):
    if not icims_configs:
        return []
    jobs = []
    failures = 0
    with ThreadPoolExecutor(max_workers=min(8, len(icims_configs))) as pool:
        futures = {pool.submit(fetch_icims, cfg, deadline): cfg for cfg in icims_configs}
        for f in futures:
            cfg = futures[f]
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("icims fetch failed for %s: %s", cfg.get("company"), e)
                failures += 1
    if failures == len(icims_configs):
        raise RuntimeError(f"icims fetcher: all {len(icims_configs)} compan(ies) failed")
    return jobs
