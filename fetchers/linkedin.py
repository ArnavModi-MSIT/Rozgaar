"""Bounded collection from LinkedIn's logged-out public job pages.

This uses the public /jobs/search/ page, not the member-only
/jobs/search-results/ route. Page availability may change at any time.
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
SEARCH_PARAMS = {"keywords": "data engineer", "location": "India", "f_TPR": "r86400"}
MAX_JOBS = 20
TIMEOUT = 15
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})
JOB_ID_RE = re.compile(r"jobPosting:(\d+)")


def _get(url, *, params=None):
    try:
        response = SESSION.get(url, params=params, timeout=TIMEOUT)
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


def collect(deadline=None):
    html = _get(SEARCH_URL, params=SEARCH_PARAMS)
    if not html:
        raise RuntimeError("linkedin public search unavailable")
    cards = BeautifulSoup(html, "html.parser").select("div.job-search-card")
    if not cards:
        raise RuntimeError("linkedin public search returned no job cards")

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
        detail = _get(job["url"])
        if not detail:
            failures += 1
        else:
            job["description"] = _description(detail)
            if not job["description"]:
                failures += 1
        jobs.append(job)
        if len(jobs) < MAX_JOBS:
            time.sleep(0.3)

    if not jobs:
        raise RuntimeError("linkedin public search had no parsable cards")
    return CollectionResult(jobs, status="partial" if failures else "ok",
                            error=f"{failures} job descriptions unavailable" if failures else "")
