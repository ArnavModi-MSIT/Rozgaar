"""India searches from Bank of America's public career pages."""

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
MAX_RESULTS_PER_SEARCH = 1000


def _description(html):
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one(".job-description-body__internal.job__external")
    return node.get_text(" ", strip=True) if node else ""


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    with requests.Session() as session:
        for label, servlet in SEARCHES:
            if deadline and time.monotonic() >= deadline:
                errors.append(f"{label}: deadline reached")
                continue
            payload = get_json(session, f"{BASE}/services/{servlet}", params={
                "start": 0, "rows": MAX_RESULTS_PER_SEARCH, "search": "jobsByLocation", "searchstring": "India",
            })
            if not isinstance(payload, dict) or not isinstance(payload.get("jobsList"), list) or not isinstance(payload.get("totalMatches"), int):
                errors.append(f"{label}: invalid listing response")
                continue
            rows, total = payload["jobsList"], payload["totalMatches"]
            if len(rows) < total:
                errors.append(f"{label}: received {len(rows)} of {total} listings")
            for row in rows:
                if deadline and time.monotonic() >= deadline:
                    errors.append(f"{label}: deadline reached while reading details")
                    break
                job_id, path = str(row.get("jobRequisitionId") or ""), row.get("jcrURL")
                if not job_id or not isinstance(path, str) or not path.startswith("/en-us/job-detail/"):
                    errors.append(f"{label}: invalid job in listing")
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
    if errors:
        if not jobs:
            raise RuntimeError("Bank of America: " + "; ".join(errors[:5]))
        log.warning("Bank of America partial collection: %s", "; ".join(errors[:5]))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))
