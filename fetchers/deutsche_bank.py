"""
Fetcher for Deutsche Bank careers (careers.db.com). Not a known ATS — runs
on "beesite" (a dedicated German HR-tech recruiting platform), found via a
real Playwright network capture:
  GET https://api-deutschebank.beesite.de/search/?data={JSON}
Unauthenticated, plain GET with the query JSON as a single `data` query
param (confirmed working with plain requests, no special headers needed).
SearchCriteria=[{"CriterionName":"PositionLocation.Country",
"CriterionValue":81}] scopes server-side to India — 81 is Deutsche Bank's
own internal country code, taken directly from the user's own
careers.db.com URL (?country=81), not guessed.

No description field is available even when explicitly requested
(PositionFormattedDescription.Content comes back as an empty object on
every record checked) — same "no per-job body in the list response"
situation as fetchers/goldman_sachs.py and fetchers/indiamart.py.

Job detail URL confirmed live via a real rendered page (the API's own
PositionURI field is a dead /index.php path that 404s on every host
tried — the real site is a client-side-routed SPA):
  https://careers.db.com/professionals/search-roles/#/professional/job/{id}

Real volume at last check: 246 India postings, 16 NCR (6.5%, New Delhi/
Gurgaon) — mostly private banking/sales roles, not engineering, but a
real signal from a genuine top-tier global bank.
"""

import json
import logging
import time

import requests

log = logging.getLogger("jobbot")

SEARCH_URL = "https://api-deutschebank.beesite.de/search/"
DETAIL_BASE = "https://careers.db.com/professionals/search-roles/#/professional/job"
INDIA_COUNTRY_CODE = 81
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
PAGE_SIZE = 50
MAX_PAGES = 20  # 246 postings / 50 per page ~= 5 pages at last check;
# generous headroom, hard cap only to guarantee termination if volume grows.

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})


def _get(first_item):
    query = {
        "LanguageCode": "en",
        "SearchParameters": {
            "FirstItem": first_item,
            "CountItem": PAGE_SIZE,
            "MatchedObjectDescriptor": [
                "PositionID", "PositionTitle",
                "PositionLocation.CityName", "PositionLocation.CountryName",
                "PositionLocation.CountrySubDivisionName",
            ],
            "Sort": [{"Criterion": "PublicationStartDate", "Direction": "DESC"}],
        },
        "SearchCriteria": [{"CriterionName": "PositionLocation.Country", "CriterionValue": INDIA_COUNTRY_CODE}],
    }
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(SEARCH_URL, params={"data": json.dumps(query)}, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def collect(deadline=None):
    jobs = []
    seen_ids = set()
    first_item = 1
    known_total = None
    page = 0
    while page < MAX_PAGES:
        if deadline is not None and time.monotonic() >= deadline:
            break
        data = _get(first_item)
        if not data:
            break
        result = data.get("SearchResult", {})
        items = result.get("SearchResultItems") or []
        if known_total is None:
            known_total = result.get("SearchResultCountAll", 0)
        if not items:
            break

        new_on_page = 0
        for it in items:
            desc = it.get("MatchedObjectDescriptor", {})
            position_id = desc.get("PositionID", "")
            if not position_id or position_id in seen_ids:
                continue
            seen_ids.add(position_id)
            locations = desc.get("PositionLocation") or []
            location = ", ".join(
                l.get("CityName", "") for l in locations if l.get("CityName")
            )
            jobs.append({
                "company": "deutsche_bank",
                "source_id": position_id,
                "title": desc.get("PositionTitle", ""),
                "location": location,
                "url": f"{DETAIL_BASE}/{position_id}",
                "description": "",
            })
            new_on_page += 1
        if new_on_page == 0:
            break
        first_item += PAGE_SIZE
        page += 1
        if known_total and first_item > known_total:
            break
        time.sleep(0.3)

    if not jobs:
        raise RuntimeError("deutsche_bank fetcher: no jobs fetched")
    return jobs
