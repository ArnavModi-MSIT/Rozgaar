"""
Fetcher for Atlassian careers — found via DevTools Network tab (not
guessed): https://www.atlassian.com/endpoint/careers/listings, a same-
origin JSON endpoint returning ALL current postings (222 at time of
testing) in ONE request — no pagination needed at all, the simplest
fetcher in this project.

Confirmed real fields: title, locations (a list — some postings have
multiple, e.g. ["Remote - Japan - Remote", "Remote - Remote"]), category,
overview/responsibilities/qualifications (HTML), applyUrl,
portalJobPost.id / id (numeric).

Interesting: applyUrl resolves to *-atlassian.icims.com — this endpoint is
Atlassian's own first-party wrapper around iCIMS data, not a different
platform. Calling iCIMS's own /jobs endpoint directly returned 405
(confirmed via debug/debug_atlassian_icims.py) — this endpoint sidesteps
that entirely.

No location scoping in the request itself (all 222 postings are global,
across every country) — India-scoping happens the same way as every other
platform, via run.py's save-time is_india_or_unknown() filter.
"""

import logging
import time

import requests

from fetchers.standard import strip_html

log = logging.getLogger("jobbot")

URL = "https://www.atlassian.com/endpoint/careers/listings"
TIMEOUT = 20  # response is ~1.5MB — more room than the usual 15s default
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
})


def _get():
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(URL, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # 4xx — don't retry
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def _parse_job(j):
    parts = []
    if j.get("overview"):
        parts.append(j["overview"])
    if j.get("responsibilities"):
        parts.append(j["responsibilities"])
    if j.get("qualifications"):
        parts.append(j["qualifications"])
    combined = "\n\n".join(parts)

    locations = j.get("locations") or []
    location = ", ".join(locations) if locations else ""

    return {
        "company": "atlassian",
        "source_id": str(j.get("id", "")),
        "title": j.get("title", ""),
        "location": location,
        "url": j.get("applyUrl", ""),
        "description": strip_html(combined, max_chars=None)[:6000] if combined else "",
    }


def fetch_all():
    data = _get()
    if not data:
        return []
    jobs = []
    for j in data:
        job = _parse_job(j)
        if job["title"]:
            jobs.append(job)
    return jobs


def collect(deadline=None):
    # Single request returns everything — no per-company config, no
    # pagination, deadline kept only for signature consistency with other
    # PLATFORMS entries.
    #
    # No try/except here (there used to be one, catching everything and
    # returning []) — this is a SINGLE request with no per-item
    # granularity to fall back on, so catching the exception here made
    # "the Atlassian API errored entirely" indistinguishable from
    # "confirmed zero India postings today" in every downstream log and
    # run_stats row. Letting it propagate reaches core/collector.py's own
    # exception handling, which correctly records status="failed".
    return fetch_all()
