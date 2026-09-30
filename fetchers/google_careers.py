"""
Fetcher for Google Careers (google.com/about/careers/applications/jobs/results)
— Google's own bespoke recruiting platform, not a common ATS others use.
Confirmed server-rendered via debug/debug_google_careers.py: title,
location, experience level, and minimum qualifications are all present in
raw HTML (card class "sMn82b", confirmed two independent ways — matched a
live DevTools inspection too). No headless browser needed despite the page
using jsaction-based click handlers instead of conventional <a href> links
for most elements — the one real anchor (class "WpHeLc") does carry a
working relative URL with the job's numeric id embedded in it.

Card structure (confirmed real against an actual card, not guessed):
  div.sMn82b
    h3.QJPWVe                                    -> title
    div.wVoYLb span.pwO9Dc.vo5qdf span.r0wTof     -> location
    span.wVSTAb                                   -> experience level (e.g. "Early")
    div.Xsxa1e ul li                               -> minimum qualifications (list)
    a.WpHeLc[href]                                 -> relative job URL; the leading
                                                       numeric token in the href's
                                                       "jobs/results/<id>-<slug>"
                                                       segment is the job id
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

from fetchers.standard import strip_html

log = logging.getLogger("jobbot")

BASE = "https://www.google.com/about/careers/applications/"
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
PAGE_SIZE = 20  # confirmed from a real response ("Showing 1 to 20 of 30 rows")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})


def _get(url):
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
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
    title_el = card.select_one("h3.QJPWVe")
    title = title_el.get_text(strip=True) if title_el else ""

    loc_el = card.select_one("div.wVoYLb span.pwO9Dc.vo5qdf span.r0wTof")
    location = loc_el.get_text(strip=True) if loc_el else ""

    level_el = card.select_one("span.wVSTAb")
    level = level_el.get_text(strip=True) if level_el else ""

    quals = [li.get_text(strip=True) for li in card.select("div.Xsxa1e ul li")]
    quals_text = "\n".join(f"- {q}" for q in quals)

    link_el = card.select_one("a.WpHeLc")
    href = link_el.get("href", "") if link_el else ""
    url = f"{BASE}{href}" if href else ""

    # Job id is the leading numeric token in the relative href, e.g.
    # "jobs/results/140309946964026054-systems-development-engineer?..."
    source_id = ""
    if href and "jobs/results/" in href:
        after_prefix = href.split("jobs/results/", 1)[-1]
        source_id = after_prefix.split("-", 1)[0]

    parts = []
    if level:
        parts.append(f"Level: {level}")
    if quals_text:
        parts.append(f"Minimum qualifications:\n{quals_text}")
    description = "\n\n".join(parts)

    return {
        "company": "google",
        "source_id": source_id,
        "title": title,
        "location": location,
        "url": url,
        "description": strip_html(description, max_chars=None)[:6000] if description else "",
    }


def fetch_google(cfg, deadline=None):
    """cfg = {"company": "google", "location": ..., "target_levels": [...]}
    target_levels are repeated as separate query params, matching the
    multi-select filter checkboxes on Google's own site (e.g. selecting
    both "Early" and "Intern & Apprentice" produces
    ?target_level=EARLY&target_level=INTERN_AND_APPRENTICE)."""
    location = cfg.get("location", "India")
    target_levels = cfg.get("target_levels", [])

    query = f"location={location}"
    for lvl in target_levels:
        query += f"&target_level={lvl}"

    jobs = []
    page = 1
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break
        url = f"{BASE}jobs/results?{query}"
        if page > 1:
            url += f"&page={page}"
        html = _get(url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="sMn82b")
        if not cards:
            break
        for card in cards:
            job = _parse_card(card)
            if job["title"]:
                jobs.append(job)
        if len(cards) < PAGE_SIZE:
            break  # short page — genuinely the last one
        page += 1
        time.sleep(0.3)  # polite gap between page requests
    return jobs


def collect(configs, deadline=None):
    # Parallelized across configs (e.g. different location/target_level
    # combinations) — was fully sequential before. Same pattern as
    # fetchers/oracle.py's collect(); pagination within a single config
    # still runs sequentially inside fetch_google() since each page
    # depends on the previous one not being short.
    if not configs:
        return []
    jobs = []
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = {pool.submit(fetch_google, cfg, deadline): cfg for cfg in configs}
        for f in futures:
            cfg = futures[f]
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("google careers fetch failed for %s: %s", cfg.get("company"), e)
    return jobs
