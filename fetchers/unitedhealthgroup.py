"""UnitedHealth Group' public TalentBrew India search and job descriptions."""

import time
import json
import re
from .standard import strip_html
from core.location import parse_country
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .http_client import get_text, get_json
from .result import CollectionResult

SEARCH_URL = "https://careers.unitedhealthgroup.com/search-jobs/india/"
MAX_PAGES = 100


def _get(url):
    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0"
        return get_text(session, url, timeout=15)


def _listing_page(page):
    with requests.Session() as session:
        session.headers["User-Agent"]="Mozilla/5.0"
        data=get_json(session,"https://careers.unitedhealthgroup.com/search-jobs/results",params={"CurrentPage":page,"RecordsPerPage":15,"Keywords":"india","SearchResultsModuleName":"Search Results","SearchType":1,"SortCriteria":0,"SortDirection":0,"SearchResultsType":0})
    return data.get("results", "") if isinstance(data,dict) else ""

def _parse_page(html, page):
    soup = BeautifulSoup(html or "", "html.parser")
    root = soup.select_one("#search-results")
    if root is None or int(root.get("data-current-page", 0)) != page or root.get("data-keywords", "").lower() != "india":
        raise RuntimeError(f"UnitedHealth Group: invalid search response on page {page}")
    total = int(root["data-total-results"])
    pages = int(root["data-total-pages"])
    jobs = []
    for link in soup.select("#search-results-list a[data-job-id]"):
        location = link.select_one(".job-location")
        jobs.append({
            "company": "unitedhealthgroup", "source_id": link["data-job-id"],
            "title": (link.select_one("h2") or link).get_text(" ", strip=True),
            "location": location.get_text(" ", strip=True) if location else "",
            "url": urljoin(SEARCH_URL, link["href"]), "description": "",
        })
    return jobs, total, pages


def _description(job, deadline):
    if deadline is not None and time.monotonic() >= deadline:
        return ""
    soup = BeautifulSoup(_get(job["url"]) or "", "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
        try:data=json.loads(script.get_text())
        except (ValueError,TypeError):continue
        if isinstance(data,dict) and data.get("@type")=="JobPosting" and data.get("description"):
            return strip_html(data["description"],max_chars=None)[:12000]
    descriptions=soup.select(".ats-description")
    return max((node.get_text(" ",strip=True) for node in descriptions),key=len,default="")[:12000]


INDIA_STATES = re.compile(r"\b(Telangana|Tamil Nadu|Karnataka|Haryana|Maharashtra|Delhi|Uttar Pradesh|Kerala|Gujarat|West Bengal|Andhra Pradesh|Punjab|Rajasthan|Madhya Pradesh|Bihar|Odisha|Chandigarh)\b",re.I)

def india_location(location):
    country=parse_country(location)
    if country=="India":return location
    if country!="Unknown":return None
    if INDIA_STATES.search(location):return location+", India"
    return None

def collect(deadline=None):
    if deadline is not None and time.monotonic()>=deadline:
        return CollectionResult(status="partial",error="deadline reached before listing")
    jobs, total, pages = _parse_page(_listing_page(1), 1)
    seen = {job["source_id"] for job in jobs}
    errors = []
    for page in range(2, min(pages, MAX_PAGES) + 1):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("search deadline reached")
            break
        try:
            batch, count, _ = _parse_page(_listing_page(page), page)
            if count != total:
                errors.append("listing total changed during collection")
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
    jobs = [dict(job,location=india_location(job["location"])) for job in jobs if india_location(job["location"])]
    with ThreadPoolExecutor(max_workers=4) as pool:
        descriptions = pool.map(lambda job: _description(job, deadline), jobs)
        for job, description in zip(jobs, descriptions):
            job["description"] = description
    missing = sum(not job["description"] for job in jobs)
    if missing:
        errors.append(f"{missing} descriptions unavailable")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
