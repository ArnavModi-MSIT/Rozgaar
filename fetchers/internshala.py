"""
Fetch public Internshala listing cards from three bounded searches:
  /internships/                         existing broad sample
  /jobs/salary-6/                       requested salary-filtered jobs
  /internships/stipend-10000/           requested stipend-filtered internships

Each search uses its own page-N path and shares one source-ID dedup set.
The HTML contains `div.individual_internship` cards for both jobs and
internships. This is a bounded sample, not a complete crawl; the live
search pages can change independently of this parser.
"""

import logging
import time

import requests
from bs4 import BeautifulSoup

from fetchers.standard import strip_html
from fetchers.result import CollectionResult

log = logging.getLogger("jobbot")

BASE = "https://internshala.com"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
MAX_PAGES = 30  # ~40-50 cards/page -> ~1200-1500 postings sampled per
# run for the existing broad internship search.
FILTERED_MAX_PAGES = 10  # limit extra requests to each requested search
SEARCHES = (
    ("internships", MAX_PAGES),
    ("jobs/salary-6", FILTERED_MAX_PAGES),
    ("internships/stipend-10000", FILTERED_MAX_PAGES),
)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})


def _get(search_path, page):
    url = f"{BASE}/{search_path}/" if page == 1 else f"{BASE}/{search_path}/page-{page}/"
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.text
        except requests.HTTPError:
            if r.status_code < 500:
                return None
        except requests.RequestException:
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def _parse_card(card):
    link_el = card.select_one("a.job-title-href")
    title = link_el.get_text(strip=True) if link_el else ""
    href = link_el.get("href", "") if link_el else ""
    url = f"{BASE}{href}" if href.startswith("/") else href

    source_id = card.get("internshipid", "") or href

    company_el = card.select_one("p.company-name")
    company = company_el.get_text(strip=True) if company_el else "Unknown"

    location_el = card.select_one("div.locations span a") or card.select_one("div.locations span")
    location = location_el.get_text(strip=True) if location_el else ""

    desc_el = card.select_one("div.about_job div.text")
    description = strip_html(desc_el.decode_contents(), max_chars=None) if desc_el else ""

    return {
        "company": company,
        "source_id": str(source_id),
        "title": title,
        "location": location,
        "url": url,
        "description": description,
    }


def _fetch_search(search_path, max_pages, seen_ids, deadline=None):
    jobs = []
    seen_on_search = set()
    page = 1
    incomplete_reason = ""
    while page <= max_pages:
        if deadline is not None and time.monotonic() >= deadline:
            incomplete_reason = f"{search_path}: deadline before page {page}"
            break
        html = _get(search_path, page)
        if not html:
            incomplete_reason = f"{search_path}: page {page} request failed"
            break
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="individual_internship")
        if not cards:
            if page == 1:
                incomplete_reason = f"{search_path}: no listing cards on page 1"
            break

        new_on_page = 0
        for card in cards:
            job = _parse_card(card)
            if not job["title"] or not job["url"] or job["source_id"] in seen_on_search:
                continue
            seen_on_search.add(job["source_id"])
            new_on_page += 1
            if job["source_id"] not in seen_ids:
                seen_ids.add(job["source_id"])
                jobs.append(job)
        if new_on_page == 0:
            break
        page += 1
        time.sleep(0.3)
    if incomplete_reason:
        if not seen_on_search:
            raise RuntimeError(incomplete_reason)
        return CollectionResult(jobs, status="partial", error=incomplete_reason)
    return CollectionResult(jobs)


def collect(deadline=None):
    jobs = []
    seen_ids = set()
    reasons = []
    failures = 0
    for search_path, max_pages in SEARCHES:
        try:
            result = _fetch_search(search_path, max_pages, seen_ids, deadline=deadline)
            jobs.extend(result)
            if result.status == "partial":
                reasons.append(result.error)
        except Exception as exc:
            log.exception("internshala '%s' failed: %s", search_path, exc)
            failures += 1
            reasons.append(str(exc))
    if failures == len(SEARCHES):
        raise RuntimeError("internshala fetcher: all searches failed")
    return CollectionResult(jobs, status="partial" if reasons else "ok", error="; ".join(reasons))
