"""Bounded collection from LinkedIn's logged-out public job pages.

Guest search and detail fragments are primary. Public job pages are a fallback.
The member-only /jobs/search-results/ route is not used. Page availability
may change at any time.
"""

import logging
import re
import time
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from fetchers.result import CollectionResult
from fetchers.standard import strip_html

log = logging.getLogger("jobbot")

SEARCH_URL = "https://www.linkedin.com/jobs/search/"
GUEST_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
GUEST_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
SEARCH_PARAMS = {"keywords": "data engineer", "location": "India", "f_TPR": "r86400"}
MAX_JOBS = 20
GUEST_PAGE_SIZE = 10
TIMEOUT = 15
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
JOB_ID_RE = re.compile(r"jobPosting:(\d+)")
REQUEST_GAP_SECONDS = 1.0


class RateLimited(RuntimeError):
    """The source asked this run to stop requesting LinkedIn pages."""


def _get(url, *, params=None):
    try:
        response = SESSION.get(url, params=params, timeout=TIMEOUT)
        if response.status_code == 429:
            raise RateLimited("linkedin returned HTTP 429; stopped this run")
        response.raise_for_status()
        if "/uas/login" in response.url or "security check" in response.text[:2000].lower():
            return None
        return response.text
    except requests.RequestException as exc:
        log.warning("linkedin request failed: %s", exc)
        return None


def _parse_card(card):
    link = card.select_one("a.base-card__full-link")
    title = card.select_one("h3.base-search-card__title")
    company = card.select_one("h4.base-search-card__subtitle")
    location = card.select_one("span.job-search-card__location")
    href = link.get("href", "") if link else ""
    parsed = urlsplit(href)
    url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    match = JOB_ID_RE.search(card.get("data-entity-urn", ""))
    return {
        "source_id": match.group(1) if match else "",
        "company": company.get_text(" ", strip=True) if company else "Unknown",
        "title": title.get_text(" ", strip=True) if title else "",
        "location": location.get_text(" ", strip=True) if location else "",
        "url": url,
        "description": "",
    }


def _description(html):
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one("div.show-more-less-html__markup")
    return strip_html(element.decode_contents(), max_chars=None) if element else ""


def _search_cards():
    cards = []
    error = ""
    for offset in range(0, MAX_JOBS, GUEST_PAGE_SIZE):
        html = _get(GUEST_SEARCH_URL, params={**SEARCH_PARAMS, "start": offset})
        page_cards = BeautifulSoup(html, "html.parser").select("li.base-card, div.job-search-card") if html else []
        if not page_cards:
            if offset == 0:
                fallback = _get(SEARCH_URL, params=SEARCH_PARAMS)
                cards = BeautifulSoup(fallback, "html.parser").select("li.base-card, div.job-search-card") if fallback else []
                if not cards:
                    raise RuntimeError("linkedin public and guest searches unavailable")
            else:
                error = f"linkedin guest search stopped at offset {offset}"
            break
        cards.extend(page_cards)
        if len(page_cards) < GUEST_PAGE_SIZE:
            break
    return cards[:MAX_JOBS], error


def collect(deadline=None):
    cards, search_error = _search_cards()

    jobs = []
    seen = set()
    failures = 0
    for card in cards:
        if len(jobs) >= MAX_JOBS:
            break
        job = _parse_card(card)
        if not job["source_id"] or not job["title"] or not job["url"] or job["source_id"] in seen:
            continue
        seen.add(job["source_id"])
        if deadline is not None and time.monotonic() >= deadline:
            return CollectionResult(jobs, status="partial", error="linkedin deadline before all descriptions")
        try:
            detail = _get(GUEST_DETAIL_URL.format(job["source_id"]))
            job["description"] = _description(detail) if detail else ""
            if not job["description"]:
                fallback = _get(job["url"])
                job["description"] = _description(fallback) if fallback else ""
        except RateLimited as exc:
            if not jobs:
                raise
            reasons = [reason for reason in (search_error, str(exc)) if reason]
            return CollectionResult(jobs, status="partial", error="; ".join(reasons))
        if not job["description"]:
            failures += 1
        jobs.append(job)
        if len(jobs) < MAX_JOBS:
            time.sleep(REQUEST_GAP_SECONDS)

    if not jobs:
        raise RuntimeError("linkedin public search had no parsable cards")
    reasons = [reason for reason in (search_error, f"{failures} job descriptions unavailable" if failures else "") if reason]
    return CollectionResult(jobs, status="partial" if reasons else "ok", error="; ".join(reasons))
