"""
Fetcher for Internshala (internshala.com) — no API at all, but genuinely
clean server-rendered HTML (confirmed: no XHR/fetch call ever fires for
the listing itself, real `<div class="individual_internship">` cards are
already in the raw response). Paginated via
  GET https://internshala.com/internships/page-N/

No filter is needed for "is this fresher-targeted" — the entire site is
internships only, by definition. A per-category URL path DOES exist on
the site (e.g. "Internships by Profile" -> data-analyst-internship/) but
was checked and found NOT to reliably scope results (a live check
against .../data-analyst-internship/ returned "Operations" as the top
two titles, not data-analyst-relevant postings) — left unscoped instead,
same "fetch broadly, let the existing TARGET_ROLE_RE relevance gate in
config.py do the real filtering downstream" pattern most fetchers in
this project already use.

~7,220 total internships at last check — MAX_PAGES caps this at a
sample (see its own comment), not an attempt at the full pool; the site
gives no reliable way to pre-filter to only the relevant slice, and
crawling all 7,220 every run would be excessive. Full description text
is already in the list response (`div.about_job div.text`) — no
separate detail-fetch needed.
"""

import logging
import time

import requests
from bs4 import BeautifulSoup

from fetchers.standard import strip_html

log = logging.getLogger("jobbot")

BASE = "https://internshala.com"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
MAX_PAGES = 30  # ~40-50 cards/page -> ~1200-1500 postings sampled per
# run, a deliberate bounded sample out of ~7,220 total (see module
# docstring) — no reliable server-side relevance filter exists here.

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})


def _get(page):
    url = f"{BASE}/internships/" if page == 1 else f"{BASE}/internships/page-{page}/"
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


def collect(deadline=None):
    jobs = []
    seen_ids = set()
    page = 1
    while page <= MAX_PAGES:
        if deadline is not None and time.monotonic() >= deadline:
            break
        html = _get(page)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="individual_internship")
        if not cards:
            break

        new_on_page = 0
        for card in cards:
            job = _parse_card(card)
            if not job["title"] or job["source_id"] in seen_ids:
                continue
            seen_ids.add(job["source_id"])
            jobs.append(job)
            new_on_page += 1
        if new_on_page == 0:
            break
        page += 1
        time.sleep(0.3)

    if not jobs:
        raise RuntimeError("internshala fetcher: no jobs fetched")
    return jobs
