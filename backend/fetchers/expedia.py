"""
Fetcher for Expedia Group careers (careers.expediagroup.com/jobs/).
Confirmed server-rendered (no JS needed). Pagination endpoint found via a
real DevTools Network-tab session (not guessed):
  GET https://careers.expediagroup.com/calc-results/?=&mypage=N
returns an HTML fragment (~9-10kB/page) with the same card structure as
the main /jobs/ page. The main page's own ?page=2 / ?from=25 params were
confirmed to NOT paginate (re-serve page 1 identically) — /calc-results/
is what the "Load More Jobs" button actually calls.

Card structure (confirmed real against a live page):
  li.Results__list__item
    a.view-job-button[href]                  -> relative job URL; the
                                                 "R-NNNNNN" path segment
                                                 is the requisition id
    h3.Results__list__title                  -> title
    h4.Results__list__location               -> location ("India - Haryāna - Gurgaon")
    p                                         -> team/department

The list gives no description body — the team name is stored as a minimal
description rather than fetching each job's detail page (~226 postings
globally, mostly non-India; per-job detail fetches for the India subset
could be added later if match quality on Expedia rows matters enough).
"""

import logging
import time

import requests
from bs4 import BeautifulSoup

from .result import CollectionResult
from .http_client import retry_after_delay, MAX_RETRY_AFTER_WAIT

log = logging.getLogger("jobbot")

BASE = "https://careers.expediagroup.com"
PAGE_URL = f"{BASE}/calc-results/"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
MAX_PAGES = 30  # ~226 postings / ~10 per fragment page — generous headroom,
# hard cap only to guarantee termination if the site's paging changes.

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE}/jobs/",
})


class ListingUnavailable(RuntimeError):
    pass


def _get(page):
    params = {"mypage": page}
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(PAGE_URL, params=params, timeout=TIMEOUT)
            if r.status_code == 429:
                wait = retry_after_delay(r.headers.get('Retry-After'), RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF)-1)])
                if attempt == RETRIES-1 or wait > MAX_RETRY_AFTER_WAIT:
                    raise ListingUnavailable(f'listing rate limited on page {page} (HTTP 429); retry after {wait:g} seconds')
                time.sleep(wait)
                continue
            if 400 <= r.status_code < 500:
                raise ListingUnavailable(f"listing request rejected on page {page} (HTTP {r.status_code})")
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.text
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # 4xx — don't retry
        except requests.RequestException:
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def _parse_card(card):
    link_el = card.select_one("a.view-job-button")
    href = link_el.get("href", "") if link_el else ""
    url = f"{BASE}{href}" if href else ""

    # Requisition id is the "R-NNNNNN" path segment, e.g.
    # /job/learning-and-development-trainer/gurgaon-hary-na/R-105579/
    source_id = ""
    if href:
        for part in reversed([p for p in href.split("/") if p]):
            if part.startswith("R-"):
                source_id = part
                break

    title_el = card.select_one("h3.Results__list__title")
    title = title_el.get_text(strip=True) if title_el else ""

    loc_el = card.select_one("h4.Results__list__location")
    location = loc_el.get_text(strip=True) if loc_el else ""

    team_el = card.select_one("p")
    team = team_el.get_text(strip=True) if team_el else ""

    return {
        "company": "expedia",
        "source_id": source_id or href,
        "title": title,
        "location": location,
        "url": url,
        "description": f"Team: {team}" if team else "",
    }


def fetch_all(deadline=None):
    jobs = []
    errors = []
    seen_ids = set()
    page = 1
    while page <= MAX_PAGES:
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("collection deadline reached")
            break
        try:
            html = _get(page)
        except ListingUnavailable as exc:
            errors.append(str(exc))
            break
        if not html:
            errors.append(f"listing request failed on page {page}")
            break
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text().lower() if soup.title else ''
        if any(text in title for text in ('just a moment','attention required','access denied')):
            errors.append(f'access challenge on page {page}')
            break
        cards = soup.find_all("li", class_="Results__list__item")
        if not cards:
            break
        new_on_page = 0
        for card in cards:
            job = _parse_card(card)
            if not job["title"]:
                continue
            # Guard against the endpoint re-serving the same page past the
            # end (same failure mode the main page's ?page= param had) —
            # a full page of already-seen ids means we're done.
            if job["source_id"] in seen_ids:
                continue
            seen_ids.add(job["source_id"])
            jobs.append(job)
            new_on_page += 1
        if new_on_page == 0:
            break
        page += 1
        time.sleep(0.3)  # polite gap between page requests
    if page > MAX_PAGES:
        errors.append("listing page limit reached")
    if errors and not jobs:
        raise RuntimeError("Expedia: " + "; ".join(errors))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))


def collect(deadline=None):
    return fetch_all(deadline=deadline)
