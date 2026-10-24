"""
Fetcher for Goldman Sachs careers (higher.gs.com). Not a known ATS — a
custom-built GraphQL platform. Found via a real Playwright network
capture: the search UI calls
  POST https://api-higher.gs.com/gateway/api/v1/graphql
      operationName=GetRoles
unauthenticated (just needs a Referer header — a plain request with no
Referer works too in testing, but this stays consistent with every other
fetcher's convention of sending one). pageSize up to 100 confirmed
working; totalCount is accurate on every page, not just the first.

No server-side location filter was found — the real UI applies one via a
`filters` array whose exact shape (RoleSearchFilterTypeInput) rejected
every plausible field name tried (value/values/filter/filterValue/code),
and driving the real filter checkbox through a headless browser hit a
click-interception issue not worth chasing further. Left unscoped instead
(1033 global at last check, small enough to paginate fully) with
client-side is_india_or_unknown() filtering doing the real scoping — same
pattern as NVIDIA/Intel/Samsung/Visa in fetchers/workday.py.

No description field exists on the search result type at all (confirmed:
adding it to the GraphQL query raises a schema validation error) — same
"no per-job body in the list response" situation Expedia/Atlassian handle
by storing a lightweight synthetic description instead of a costly
detail-page fetch. Division/job function/skills are the only descriptive
fields available, so those are joined into `description` here.

Job detail URL confirmed live: https://higher.gs.com/roles/{sourceId}
"""

import logging
import time

import requests

log = logging.getLogger("jobbot")

URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
DETAIL_BASE = "https://higher.gs.com/roles"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
PAGE_SIZE = 100
MAX_PAGES = 20  # 1033 postings / 100 per page ~= 11 pages at last check;
# generous headroom, hard cap only to guarantee termination if volume grows.

_QUERY = (
    "query GetRoles($searchQueryInput: RoleSearchQueryInput!) {\n"
    "  roleSearch(searchQueryInput: $searchQueryInput) {\n"
    "    totalCount\n"
    "    items {\n"
    "      roleId\n      corporateTitle\n      jobTitle\n      jobFunction\n"
    "      locations { primary state country city __typename }\n"
    "      status\n      division\n      skills\n"
    "      jobType { code description __typename }\n"
    "      externalSource { sourceId __typename }\n"
    "      __typename\n    }\n    __typename\n  }\n}"
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Referer": "https://higher.gs.com/",
})


def _get(page_number):
    payload = {
        "operationName": "GetRoles",
        "variables": {
            "searchQueryInput": {
                "page": {"pageSize": PAGE_SIZE, "pageNumber": page_number},
                "sort": {"sortStrategy": "RELEVANCE", "sortOrder": "DESC"},
                "filters": [],
                "experiences": ["EARLY_CAREER", "PROFESSIONAL"],
                "searchTerm": "",
            }
        },
        "query": _QUERY,
    }
    for attempt in range(RETRIES):
        try:
            r = SESSION.post(URL, json=payload, timeout=TIMEOUT)
            if r.status_code == 429:
                time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            data = r.json()
            if data.get("errors"):
                log.warning("goldman_sachs: GraphQL error: %s", data["errors"][0].get("message", ""))
                return None
            return data.get("data", {}).get("roleSearch")
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # other 4xx — don't retry
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def collect(deadline=None):
    jobs = []
    seen_ids = set()
    page_number = 0
    known_total = None
    while page_number < MAX_PAGES:
        if deadline is not None and time.monotonic() >= deadline:
            break
        result = _get(page_number)
        if not result:
            break
        items = result.get("items") or []
        if known_total is None:
            known_total = result.get("totalCount", 0)
        if not items:
            break

        new_on_page = 0
        for j in items:
            source_id = (j.get("externalSource") or {}).get("sourceId", "")
            if not source_id or source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            locations = j.get("locations") or []
            location = ", ".join(
                f"{l.get('city', '')}, {l.get('country', '')}".strip(", ")
                for l in locations if l.get("city") or l.get("country")
            )
            desc_parts = [j.get("division", ""), j.get("jobFunction", "")]
            desc_parts += j.get("skills") or []
            description = " | ".join(p for p in desc_parts if p)
            jobs.append({
                "company": "goldman_sachs",
                "source_id": source_id,
                "title": j.get("jobTitle", ""),
                "location": location,
                "url": f"{DETAIL_BASE}/{source_id}",
                "description": description,
            })
            new_on_page += 1
        if new_on_page == 0:
            break
        page_number += 1
        if known_total and len(jobs) >= known_total:
            break
        time.sleep(0.3)

    if not jobs:
        raise RuntimeError("goldman_sachs fetcher: no jobs fetched")
    return jobs
