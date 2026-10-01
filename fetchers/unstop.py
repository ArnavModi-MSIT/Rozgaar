"""
Fetcher for Unstop (unstop.com) — a real, public, unauthenticated API:
  GET https://unstop.com/api/public/opportunity/search-result
      ?opportunity=jobs&page=N&per_page=50&oppstatus=open
Confirmed live via a real Playwright network capture, then verified
directly with plain `requests` (no special headers/Referer needed, unlike
several ATS platforms this project has hit). Response:
  {"data": {"data": [...], "total", "current_page", "last_page", ...}}

Unlike this project's other multi-company platforms (Workday/Oracle/etc,
one company per config entry), Unstop is a genuine multi-employer
aggregator — closer in shape to the LinkedIn/Indeed fetchers removed
earlier this project, EXCEPT the data quality here is real, not a title
guess: every posting carries `jobDetail.min_experience`/`max_experience`
as actual integers, plus an explicit `filters` array tagging the posting
"Fresher" vs "Experienced Professionals" — Unstop's own HR-side
classification, the same class of signal Workday's workerSubType facet
provided (see config.py's _FRESHER_SIGNAL comment), not a regex guess.

The real experience number is injected into the stored description
(`Experience required: N years.`) rather than adding a new DB column —
this lets the EXISTING core/experience.extract_min_experience() pick up
the exact real number Unstop already computed, instead of re-guessing it
from prose, with zero schema changes (same "prefer enrichment over new
infrastructure" call already made for the Workday facet investigation).

Confirmed live: jobs include Fresher-tagged postings, all India-located in
a sample checked (no country
filter needed or found). Full HTML description included per posting
(`details` field) — no separate detail-fetch needed.
"""

import time

import requests

from fetchers.result import CollectionResult

SEARCH_URL = "https://unstop.com/api/public/opportunity/search-result"
DETAIL_BASE = "https://unstop.com"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
PAGE_SIZE = 50
MAX_PAGES = 30  # hard cap to guarantee termination if volume grows.

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
})


def _get(opportunity_type, page):
    params = {"opportunity": opportunity_type, "page": page, "per_page": PAGE_SIZE, "oppstatus": "open"}
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(SEARCH_URL, params=params, timeout=TIMEOUT)
            if r.status_code == 429:
                time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json().get("data", {})
        except requests.HTTPError:
            if r.status_code < 500:
                return None
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def _location_str(item):
    locations = item.get("locations") or []
    parts = []
    for l in locations:
        city = l.get("city") or ""
        country = l.get("country") or ""
        parts.append(", ".join(p for p in (city, country) if p))
    return "; ".join(p for p in parts if p)


def _fetch_type(opportunity_type, deadline=None):
    jobs = []
    seen_ids = set()
    page = 1
    known_total = None
    incomplete_reason = ""
    while page <= MAX_PAGES:
        if deadline is not None and time.monotonic() >= deadline:
            incomplete_reason = f"{opportunity_type}: deadline reached before page {page}"
            break
        data = _get(opportunity_type, page)
        if data is None:
            incomplete_reason = f"{opportunity_type}: page {page} request failed"
            break
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            incomplete_reason = f"{opportunity_type}: page {page} response missing postings list"
            break
        items = data["data"]
        if known_total is None:
            known_total = data.get("total", 0)
        if not items:
            if known_total and len(seen_ids) < known_total:
                incomplete_reason = f"{opportunity_type}: empty page {page} before reported total"
            break

        new_on_page = 0
        for item in items:
            source_id = str(item.get("id", ""))
            if not source_id or source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            org = item.get("organisation") or {}
            company = org.get("name") or "Unknown"

            job_detail = item.get("jobDetail") or {}
            min_exp = job_detail.get("min_experience")
            description = item.get("details") or ""
            if min_exp is not None:
                description = f"{description}\n\nExperience required: {min_exp} years."

            filters = item.get("filters") or []
            is_fresher_tagged = any(f.get("name") == "Fresher" for f in filters)
            if is_fresher_tagged and min_exp is None:
                description = f"{description}\n\nFresher-eligible (0 years experience)."

            url = item.get("seo_url") or (
                f"{DETAIL_BASE}/{item['public_url']}" if item.get("public_url") else ""
            )

            jobs.append({
                "company": company,
                "source_id": source_id,
                "title": item.get("title", ""),
                "location": _location_str(item),
                "url": url,
                "description": description,
            })
            new_on_page += 1
        if new_on_page == 0:
            if known_total and len(seen_ids) < known_total:
                incomplete_reason = f"{opportunity_type}: page {page} repeated existing IDs"
            break
        page += 1
        if known_total and (page - 1) * PAGE_SIZE >= known_total:
            break
        time.sleep(0.3)
    if page > MAX_PAGES and known_total and len(seen_ids) < known_total:
        incomplete_reason = f"{opportunity_type}: stopped at {MAX_PAGES}-page cap"
    if incomplete_reason and not jobs:
        raise RuntimeError(incomplete_reason)
    return CollectionResult(jobs, status="partial" if incomplete_reason else "ok", error=incomplete_reason)


def collect(deadline=None):
    return _fetch_type("jobs", deadline=deadline)
