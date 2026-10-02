"""Tesco official India careers search and job descriptions."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .result import CollectionResult

SEARCH_URL = "https://careers.tesco.com/en_GB/careers/SearchJobs/?12328=%5B587056%5D&12328_format=7246&listFilterMode=1&jobRecordsPerPage=10"

def _get(url):
    with requests.Session() as session: return get_text(session, url)

def _page(html):
    soup = BeautifulSoup(html or "", "html.parser")
    total = re.search(r"\d+\s*-\s*\d+\s+of\s+(\d+)\s+results", soup.get_text(" ",strip=True))
    jobs = []
    for link in soup.select('.article__header__text__title a[href*="JobDetail"]'):
        block = link.find_parent(class_="article__header__text")
        location = block.select_one(".list-item-location")
        url = link["href"]
        jobs.append({"company":"tesco", "source_id":url.rstrip("/").rsplit("/",1)[-1], "title":link.get_text(" ",strip=True), "location":location.get_text(" ",strip=True) if location else "", "url":url, "description":""})
    if total is None: raise RuntimeError("Tesco search total unavailable")
    return jobs, int(total.group(1))

def _description(job, deadline):
    if deadline is not None and time.monotonic() >= deadline: return ""
    soup = BeautifulSoup(_get(job["url"]) or "", "html.parser")
    fields = soup.select(".article__content__view__field")
    return "\n".join(field.get_text(" ",strip=True) for field in fields)[:12000]

def collect(deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    for offset in range(0, 1000, 10):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("deadline reached"); break
        try: batch, count = _page(_get(SEARCH_URL + f"&jobOffset={offset}"))
        except RuntimeError:
            if not jobs: raise
            errors.append(f"listing offset {offset} failed"); break
        if total is None: total = count
        fresh = [job for job in batch if job["source_id"] not in seen]
        jobs.extend(fresh); seen.update(job["source_id"] for job in fresh)
        if len(jobs) >= total: break
        if not fresh: errors.append("repeated or empty listing page"); break
    else: errors.append("page limit reached")
    if total is None or len(jobs) != total: errors.append(f"received {len(jobs)} of {total} listings")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, desc in zip(jobs, pool.map(lambda job: _description(job, deadline), jobs)):
            job["description"] = desc
            if not desc: errors.append("description unavailable: " + job["source_id"])
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
