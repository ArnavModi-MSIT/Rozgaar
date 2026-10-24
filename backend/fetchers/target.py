"""Target's public TalentBrew India search and job descriptions."""

import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .http_client import get_text
from .result import CollectionResult

SEARCH_URL = "https://indiajobs.target.com/search-jobs"
MAX_PAGES = 100


def _get(url):
    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0"
        return get_text(session, url, timeout=15)


def _parse_page(html, page):
    soup = BeautifulSoup(html or "", "html.parser")
    root = soup.select_one("#search-results")
    if root is None or int(root.get("data-current-page", 0)) != page:
        raise RuntimeError(f"Target: invalid search response on page {page}")
    total = int(root["data-total-results"])
    pages = int(root["data-total-pages"])
    jobs = []
    for link in soup.select("#search-results-list a[data-job-id]"):
        location = link.select_one(".job-location .section3__job-info") or link.select_one(".job-location")
        jobs.append({
            "company": "target", "source_id": link["data-job-id"],
            "title": (link.select_one("h2") or link).get_text(" ", strip=True),
            "location": location.get_text(" ", strip=True) + ", India" if location else "India",
            "url": urljoin(SEARCH_URL, link["href"]), "description": "",
        })
    return jobs, total, pages


def _description(job, deadline):
    if deadline is not None and time.monotonic() >= deadline:
        return ""
    soup = BeautifulSoup(_get(job["url"]) or "", "html.parser")
    for element in soup.select(".job-description__buttons"):
        element.decompose()
    description = soup.select_one(".ats-description")
    return description.get_text(" ", strip=True) if description else ""


def collect(deadline=None):
    jobs, total, pages = _parse_page(_get(SEARCH_URL), 1)
    seen = {job["source_id"] for job in jobs}
    errors = []
    for page in range(2, min(pages, MAX_PAGES) + 1):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("search deadline reached")
            break
        try:
            batch, _, _ = _parse_page(_get(f"{SEARCH_URL}?p={page}"), page)
        except (RuntimeError, ValueError, KeyError) as exc:
            errors.append(str(exc))
            break
        fresh = [job for job in batch if job["source_id"] not in seen]
        if not fresh:
            errors.append(f"page {page} returned no new postings")
            break
        jobs.extend(fresh)
        seen.update(job["source_id"] for job in fresh)
    if len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")
    with ThreadPoolExecutor(max_workers=4) as pool:
        descriptions = pool.map(lambda job: _description(job, deadline), jobs)
        for job, description in zip(jobs, descriptions):
            job["description"] = description
    missing = sum(not job["description"] for job in jobs)
    if missing:
        errors.append(f"{missing} descriptions unavailable")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
