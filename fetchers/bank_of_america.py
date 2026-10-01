"""Bounded India searches from Bank of America's public career pages."""

import logging
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from fetchers.http_client import get_json, get_text
from fetchers.result import CollectionResult

log = logging.getLogger("jobbot")
BASE = "https://careers.bankofamerica.com"
SEARCHES = (("general", "jobssearchservlet"), ("students", "campusjobssearchservlet"))
PAGE_SIZE = 10
MAX_PER_SEARCH = 30


def _description(html):
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one(".job-description-body__internal.job__external")
    return node.get_text(" ", strip=True) if node else ""


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    with requests.Session() as session:
        for label, servlet in SEARCHES:
            for start in range(0, MAX_PER_SEARCH, PAGE_SIZE):
                if deadline and time.monotonic() >= deadline:
                    errors.append(f"{label}: deadline reached")
                    break
                payload = get_json(session, f"{BASE}/services/{servlet}", params={
                    "start": start, "rows": PAGE_SIZE, "search": "jobsByLocation", "searchstring": "India",
                })
                if not isinstance(payload, dict) or not isinstance(payload.get("jobsList"), list) or not isinstance(payload.get("totalMatches"), int):
                    errors.append(f"{label}: invalid listing response at offset {start}")
                    break
                rows, total = payload["jobsList"], payload["totalMatches"]
                if not rows and start < total:
                    errors.append(f"{label}: missing listing rows at offset {start}")
                    break
                for row in rows:
                    if deadline and time.monotonic() >= deadline:
                        errors.append(f"{label}: deadline reached while reading details")
                        break
                    job_id, path = str(row.get("jobRequisitionId") or ""), row.get("jcrURL")
                    if not job_id or not isinstance(path, str) or not path.startswith("/en-us/job-detail/"):
                        errors.append(f"{label}: invalid job in offset {start}")
                        continue
                    if job_id in seen:
                        continue
                    seen.add(job_id)
                    url = urljoin(BASE, path)
                    html = get_text(session, url)
                    description = _description(html) if html else ""
                    if not description:
                        errors.append(f"{label}: description unavailable for {job_id}")
                    jobs.append({
                        "company": "Bank of America", "source_id": job_id,
                        "title": row.get("postingTitle") or "Untitled job",
                        "location": row.get("location") or row.get("primaryLocation") or "India",
                        "url": url, "description": description,
                    })
                if deadline and time.monotonic() >= deadline:
                    break
                if start + len(rows) >= total or len(rows) < PAGE_SIZE:
                    break
    if errors:
        if not jobs:
            raise RuntimeError("Bank of America: " + "; ".join(errors[:5]))
        log.warning("Bank of America partial collection: %s", "; ".join(errors[:5]))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))
