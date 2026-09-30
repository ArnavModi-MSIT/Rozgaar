"""
Fetcher for Workable — public, no-auth widget API used by Workable's own
embeddable careers widget. Confirmed field names via a working third-party
integration (job.shortcode, job.title, job.location.location_str, job.url).

Endpoint: https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
details=true is required to get description/full_description on each job;
without it you only get summary fields.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from .standard import strip_html

log = logging.getLogger("jobbot")
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "jobbot/1.0"


def _get(url):
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # 4xx — don't retry (wrong slug, account disabled)
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def fetch_workable(slug):
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    if not data:
        return []
    jobs = []
    for j in data.get("jobs", []):
        loc = j.get("location") or {}
        location = loc.get("location_str", "") or ", ".join(
            p for p in [loc.get("city", ""), loc.get("region", ""), loc.get("country", "")] if p
        )
        shortcode = j.get("shortcode", "")
        description = f"{j.get('description', '')} {j.get('full_description', '')}".strip()
        jobs.append({
            "company": slug,
            "source_id": shortcode,
            "title": j.get("title", ""),
            "location": location,
            "url": j.get("url") or j.get("shortlink") or f"https://apply.workable.com/{slug}/j/{shortcode}/",
            "description": strip_html(description, max_chars=None)[:6000],
        })
    return jobs


def collect(slugs):
    if not slugs:
        return []
    jobs = []
    with ThreadPoolExecutor(max_workers=min(8, len(slugs))) as pool:
        futures = [pool.submit(fetch_workable, slug) for slug in slugs]
        for f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("a workable company fetch failed: %s", e)
    return jobs
