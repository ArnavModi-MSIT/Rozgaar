"""Collect the official Deloitte India category with source health checks."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from backend.fetchers.http_client import get_text
from backend.fetchers.result import CollectionResult
from backend.fetchers import successfactors as sf

HOST = "southasiacareers.deloitte.com"
PATH = "/go/Deloitte-India/718244/"
CFG = {"company": "deloitte", "host": HOST}


def collect(deadline=None):
    jobs, seen, errors = [], set(), []
    total = None
    for page in range(sf.MAX_PAGES):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("listing deadline reached")
            break
        html = get_text(sf.SESSION, f"https://{HOST}{PATH}{page * sf.PAGE_SIZE}/?q=&sortColumn=referencedate&sortDirection=desc")
        if not html:
            if not jobs:
                raise RuntimeError("Deloitte India listing request failed")
            errors.append(f"page {page + 1} failed")
            break
        soup = BeautifulSoup(html, "html.parser")
        count = re.search(r"Results\s+[\d,]+\s*[–-]\s*[\d,]+\s+of\s+([\d,]+)", soup.get_text(" ", strip=True))
        if count and total is None:
            total = int(count.group(1).replace(",", ""))
        rows = soup.select("tr.data-row")
        added = 0
        for row in rows:
            job = sf._parse_row(row, CFG)
            if job and job["source_id"] not in seen:
                seen.add(job["source_id"])
                jobs.append(job)
                added += 1
        if total is not None and len(jobs) >= total:
            break
        if len(rows) < sf.PAGE_SIZE or not added:
            break
    else:
        errors.append("listing page limit reached")
    if total is None:
        errors.append("listing total unavailable")
    elif len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")

    def detail(job):
        href = job.pop("_href", "")
        if deadline is not None and time.monotonic() >= deadline:
            return False
        job["description"] = sf.fetch_job_description(HOST, href)
        return bool(job["description"])

    with ThreadPoolExecutor(max_workers=4) as pool:
        missing = sum(not ok for ok in pool.map(detail, jobs))
    if missing:
        errors.append(f"{missing} descriptions unavailable or deadline reached")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
