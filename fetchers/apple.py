"""
Fetcher for Apple's careers site (jobs.apple.com). Not a known ATS — a
custom-built platform. No separate JSON API was found (Playwright network
capture, networkidle wait, showed no job-search XHR/fetch at all) — the
real job data is server-side rendered directly into the page as a React
Router hydration blob:
  <script>window.__staticRouterHydrationData = JSON.parse("...")</script>
The quoted string is a JSON-encoded JSON string (double-encoded — parse it
twice: once to unescape the JS string literal, once to get the real
object). Real path to the job list:
  data["loaderData"]["search"]["searchResults"]  (list, 20/page)
  data["loaderData"]["search"]["totalRecords"]   (int, real total)

Search URL: GET https://jobs.apple.com/en-in/search?location=india-INDC&page=N
  location=india-INDC is Apple's own location code for all of India
  (postLocationId "postLocation-INDC" in the response) — confirmed live to
  genuinely scope server-side, not a client-side filter.

Detail URL confirmed live:
  https://jobs.apple.com/en-in/details/{positionId}/{transformedPostingTitle}?team={teamCode}
Every field needed is already in the search response itself
(jobSummary = full description), so no separate detail fetch is needed —
same simplicity win as fetchers/capgemini.py had before it was removed.

Real India volume at last check: 171 postings, heavily Bengaluru (79) and
Hyderabad (61) — Apple's real India engineering hub. Only 4 NCR hits
(Noida/Gurugram/Delhi), mostly retail/sales roles, not core engineering —
added anyway for the real India-wide tech volume and because Apple is
unambiguously a top-tier high-paying/high-growth company, same "broad
India, not NCR-exclusive" precedent as NVIDIA/Visa/Walmart.
"""

import logging
import re
import time
import json

import requests

log = logging.getLogger("jobbot")

SEARCH_URL = "https://jobs.apple.com/en-in/search"
DETAIL_BASE = "https://jobs.apple.com/en-in/details"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
MAX_PAGES = 20  # 171 postings / 20 per page ~= 9 pages at last check;
# generous headroom, hard cap only to guarantee termination if volume grows.

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})

_HYDRATION_RE = re.compile(
    r'window\.__staticRouterHydrationData = JSON\.parse\("(.*?)"\);', re.S
)


def _get(page):
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(SEARCH_URL, params={"location": "india-INDC", "page": page}, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.text
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # other 4xx — don't retry
        except requests.RequestException:
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def _parse_hydration(html):
    m = _HYDRATION_RE.search(html)
    if not m:
        return None
    try:
        inner = json.loads('"' + m.group(1) + '"')
        return json.loads(inner)
    except (ValueError, json.JSONDecodeError):
        return None


def collect(deadline=None):
    jobs = []
    seen_ids = set()
    page = 1
    known_total = None
    while page <= MAX_PAGES:
        if deadline is not None and time.monotonic() >= deadline:
            break
        html = _get(page)
        if not html:
            break
        data = _parse_hydration(html)
        if not data:
            break
        search = (data.get("loaderData") or {}).get("search") or {}
        results = search.get("searchResults") or []
        if known_total is None:
            known_total = search.get("totalRecords", 0)
        if not results:
            break

        new_on_page = 0
        for j in results:
            position_id = j.get("positionId", "")
            if not position_id or position_id in seen_ids:
                continue
            seen_ids.add(position_id)
            locations = j.get("locations") or []
            location = ", ".join(l.get("name", "") for l in locations if l.get("name"))
            slug = j.get("transformedPostingTitle", "")
            team_code = (j.get("team") or {}).get("teamCode", "")
            url = f"{DETAIL_BASE}/{position_id}/{slug}?team={team_code}" if slug else ""
            jobs.append({
                "company": "apple",
                "source_id": position_id,
                "title": j.get("postingTitle", ""),
                "location": location,
                "url": url,
                "description": j.get("jobSummary", ""),
            })
            new_on_page += 1
        if new_on_page == 0:
            break
        page += 1
        if known_total and len(jobs) >= known_total:
            break
        time.sleep(0.3)

    if not jobs:
        raise RuntimeError("apple fetcher: no jobs fetched")
    return jobs
