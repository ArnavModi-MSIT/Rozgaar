"""Public India listings from Avature career sites, with full job-page descriptions.

cfg keys: company, host, path (site base such as "/en_US/careers"), query (the tenant's own
location-filter query string, copied from a filtered search URL, e.g.
"10671=%5B871433%5D&10671_format=21337&listFilterMode=1").
Search pages are `<path>/SearchJobs/?<query>&jobRecordsPerPage=N&jobOffset=K`; the server may
cap N (Macquarie serves 9), so the offset advances by the rows actually returned.
Job pages are `<path>/JobDetail?jobId=ID`. Verified on Macquarie on 2 November 2026: 77 unique
postings, Gurugram/Hyderabad/Mumbai, the filter being the employer's own India selection.
Avature tenants differ in markup; confirm each before registering one.
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlsplit

import requests
from bs4 import BeautifulSoup

from .http_client import get_text
from .result import CollectionResult
from .standard import _expansion_location

PER_PAGE = 50
MAX_PAGES = 200


def _location(text):
    """Avature shows office labels such as "Gurugram Office"; keep anchored Indian cities only."""
    text = re.sub(r"\s+office\s*$", "", (text or "").strip(), flags=re.I)
    return _expansion_location(text)


def parse_results(html, host):
    """(jobs, total, rows_on_page). Rows whose location is not clearly Indian are dropped."""
    soup = BeautifulSoup(html or "", "html.parser")
    match = re.search(r"(\d[\d,]*)\s+results?", soup.get_text(" ", strip=True))
    total = int(match.group(1).replace(",", "")) if match else None
    articles = soup.select("article.article--result")
    jobs = []
    for article in articles:
        link = article.select_one("a[href*='JobDetail']")
        if link is None:
            raise ValueError("listing link unavailable")
        url = link["href"]
        ids = parse_qs(urlsplit(url).query).get("jobId")
        if urlsplit(url).hostname != host or not ids or not ids[0].isdigit():
            raise ValueError("listing identity unavailable")
        location = ""
        for data in article.select(".article__details__data"):
            image = data.select_one("img")
            if image is not None and "location" in (image.get("alt") or "").lower():
                paragraph = data.select("p")
                location = paragraph[-1].get_text(" ", strip=True) if paragraph else ""
        title = link.get_text(" ", strip=True)
        place = _location(location)
        if not title:
            raise ValueError("listing title unavailable")
        if place:
            jobs.append({"source_id": ids[0], "title": title, "location": place, "url": url, "description": ""})
    return jobs, total, len(articles)


def parse_detail(html):
    """(title, description). Description is the unlabeled content blocks, not the metadata fields."""
    soup = BeautifulSoup(html or "", "html.parser")
    title = soup.select_one("h2.title--11")
    blocks = []
    for field in soup.select(".article__content__view__field"):
        classes = " ".join(field.get("class") or [])
        if "field--" in classes:
            continue  # location, id, date, term, category
        text = field.get_text("\n", strip=True)
        if text:
            blocks.append(text)
    return (title.get_text(" ", strip=True) if title else ""), "\n\n".join(blocks)


def fetch(cfg, deadline=None):
    host, path, company = cfg["host"], cfg["path"].rstrip("/"), cfg["company"]
    base = f"https://{host}{path}"
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0"
        offset = 0
        for _ in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("listing deadline reached")
                break
            html = get_text(session, f"{base}/SearchJobs/?{cfg['query']}&jobRecordsPerPage={PER_PAGE}&jobOffset={offset}")
            if not html:
                if not jobs:
                    raise RuntimeError(f"Avature {host}: listing unavailable")
                errors.append(f"offset {offset} unavailable")
                break
            try:
                batch, count, rows = parse_results(html, host)
            except ValueError as exc:
                if not jobs:
                    raise RuntimeError(f"Avature {host}: {exc}") from exc
                errors.append(str(exc))
                break
            if total is None:
                total = count
            if not rows:
                break
            fresh = [job for job in batch if job["source_id"] not in seen]
            for job in fresh:
                seen.add(job["source_id"])
                jobs.append(job)
            if not fresh and rows and all(a in seen for a in re.findall(r"jobId=(\d+)", html)):
                errors.append("repeated listing page")
                break
            offset += rows
            if total is not None and offset >= total:
                break
            time.sleep(0.2)
        else:
            errors.append("listing page limit reached")

    def detail(job):
        if deadline is not None and time.monotonic() >= deadline:
            return ""
        with requests.Session() as session:
            html = get_text(session, f"{base}/JobDetail?jobId={job['source_id']}")
        title, text = parse_detail(html)
        return text if title.strip() == job["title"].strip() else ""  # never attach another job's text

    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, text in zip(jobs, pool.map(detail, jobs)):
            job["description"] = text
            job["company"] = company
            if not text:
                errors.append("description unavailable: " + job["source_id"])
    if not jobs:
        raise RuntimeError(f"Avature {host}: no India listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))
