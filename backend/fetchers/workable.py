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
from .result import CollectionResult

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
    if not isinstance(data,dict) or not isinstance(data.get("jobs"),list):
        raise RuntimeError("Workable board unavailable: "+slug)
    jobs = {}
    for j in data.get("jobs", []):
        locations = j.get("locations") or [j.get("location") or {
            "country": j.get("country", ""), "city": j.get("city", ""), "region": j.get("state", "")
        }]
        if slug in {"amagi", "tiger-analytics", "innovaccer-analytics"}:
            locations = [loc for loc in locations if
                         (loc.get("country_code") or loc.get("countryCode") or "").upper() == "IN"
                         or (loc.get("country") or "").lower() == "india"]
        if not locations:
            continue
        location = "; ".join(dict.fromkeys(loc.get("location_str") or ", ".join(
            p for p in [loc.get("city", ""), loc.get("region", ""), loc.get("country", "")] if p
        ) for loc in locations))
        shortcode = j.get("shortcode", "")
        description = f"{j.get('description', '')} {j.get('full_description', '')}".strip()
        if not shortcode or not j.get("title"):
            raise RuntimeError("Workable listing ID or title missing: " + slug)
        if shortcode in jobs:
            previous = jobs[shortcode]["location"]
            jobs[shortcode]["location"] = "; ".join(dict.fromkeys([previous, location]))
            continue
        jobs[shortcode] = {
            "company": slug,
            "source_id": shortcode,
            "title": j.get("title", ""),
            "location": location,
            "url": j.get("url") or j.get("shortlink") or f"https://apply.workable.com/{slug}/j/{shortcode}/",
            "description": strip_html(description, max_chars=None),
        }
    return list(jobs.values())


def collect(slugs):
    if not slugs:
        return []
    jobs,errors = [],[]
    with ThreadPoolExecutor(max_workers=min(8, len(slugs))) as pool:
        futures = [pool.submit(fetch_workable, slug) for slug in slugs]
        for f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("a workable company fetch failed: %s", e)
                errors.append(str(e))
    if errors and not jobs: raise RuntimeError("; ".join(errors))
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors))
