"""
Fetcher for Eightfold PCSX-powered career portals (apply.{company}.com).
Confirmed against UKG via debug/debug_ukg.py:
  GET https://{host}/api/pcsx/search?domain={domain}&query=&location={loc}
      &start=N&sort_by=timestamp
  -> {"data": {"positions": [...], "count": <int>, ...}}
Unauthenticated, 10 positions/page, start-offset pagination. The
location param genuinely filters server-side (location=India returned
exclusively Pune/Noida/Bangalore postings).

Position fields (confirmed): id, displayJobId, name, locations (list of
"City,State,Country" strings), department, positionUrl, atsJobId.

Limitation: the per-job description endpoint (/api/pcsx/match_details)
returns an empty payload without an authenticated session — descriptions
are NOT available, so like fetchers/expedia.py this stores a minimal
"Department: X" description. The older non-PCSX Eightfold API
(/api/apply/v2/jobs) is also closed here ("Not authorized for PCSX").

cfg = {"company": ..., "host": "apply.ukg.com", "domain": "ukg.com",
       "location": "India" (optional server-side filter)}
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

log = logging.getLogger("jobbot")

TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
PAGE_SIZE = 10  # PCSX serves 10 per page regardless of any num param
MAX_PAGES = 80  # hard cap for termination safety (800 postings). Raised
# from 50 (500) after Qualcomm was added: its API reports 555 India
# postings but a run stopped at exactly 500 — the cap, not the data, was
# the stop condition, silently discarding the rest. Hitting this cap is
# now logged as a warning (see fetch_eightfold) rather than passing as a
# normal result. Every other configured tenant stops naturally well
# before this, so the higher ceiling costs them nothing.

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
})


def _get(host, params):
    url = f"https://{host}/api/pcsx/search"
    headers = {"Referer": f"https://{host}/careers"}
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(url, params=params, headers=headers, timeout=TIMEOUT)
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


def _parse_position(p, cfg):
    locations = p.get("locations") or []
    # Entries look like "Noida,UP,India" — normalize commas to ", " so the
    # shared location parsing (parse_city/parse_country) reads them cleanly.
    location = "; ".join(", ".join(t.strip() for t in loc.split(",")) for loc in locations)

    pid = p.get("id", "")
    url = p.get("positionUrl") or f"https://{cfg['host']}/careers?pid={pid}&domain={cfg['domain']}"
    if url.startswith("/"):
        url = f"https://{cfg['host']}{url}"

    dept = p.get("department", "")
    return {
        "company": cfg["company"],
        "source_id": str(pid),
        "title": p.get("name", ""),
        "location": location,
        "url": url,
        "description": f"Department: {dept}" if dept else "",
    }


def fetch_eightfold(cfg, deadline=None):
    host = cfg["host"]
    jobs = []
    seen = set()
    start = 0
    total = None
    for _ in range(MAX_PAGES):
        if deadline is not None and time.monotonic() >= deadline:
            break
        params = {
            "domain": cfg["domain"],
            "query": "",
            "location": cfg.get("location", ""),
            "start": start,
            "sort_by": "timestamp",
        }
        data = _get(host, params)
        if not data:
            break
        d = data.get("data") or {}
        positions = d.get("positions") or []
        if total is None:
            total = d.get("count")
        if not positions:
            break
        new = 0
        for p in positions:
            job = _parse_position(p, cfg)
            if not job["title"]:
                continue
            # Dedup key: prefer the real source_id, but a missing/empty id
            # (seen on at least some PCSX tenants) must NOT fall back to a
            # shared "" key — that collapsed every id-less posting after
            # the first into a false duplicate. Fall back to
            # title+location instead, which still catches genuine repeat
            # pages without conflating distinct postings that merely lack
            # an id.
            dedup_id = job["source_id"] or f"{job['title']}|{job['location']}"
            if dedup_id in seen:
                continue
            seen.add(dedup_id)
            jobs.append(job)
            new += 1
        if new == 0:
            break  # endpoint re-serving old pages — done
        start += PAGE_SIZE
        if total is not None and start >= total:
            break
        time.sleep(0.3)
    else:
        # for/else: only reached when the loop ran all MAX_PAGES times
        # without ever breaking — i.e. the tenant still had more to give
        # and the cap, not the data, is what stopped us. Logged loudly so
        # a truncated result is never mistaken for a complete one.
        log.warning(
            "eightfold %s: stopped at the MAX_PAGES cap (%d pages, %d postings, "
            "tenant reports %s total) — results are TRUNCATED",
            cfg.get("company"), MAX_PAGES, len(jobs), total,
        )
    return jobs


def collect(configs, deadline=None):
    if not configs:
        return []
    jobs = []
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = {pool.submit(fetch_eightfold, cfg, deadline): cfg for cfg in configs}
        for f in futures:
            cfg = futures[f]
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("eightfold fetch failed for %s: %s", cfg.get("company"), e)
    return jobs
