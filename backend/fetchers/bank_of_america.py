"""India searches from Bank of America's public career pages."""

import logging
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from backend.fetchers.http_client import get_json, get_text
from backend.fetchers.result import CollectionResult

log = logging.getLogger("jobbot")
BASE = "https://careers.bankofamerica.com"
SEARCHES = (("general", "jobssearchservlet"), ("students", "campusjobssearchservlet"))
MAX_RESULTS_PER_SEARCH = 1000
PAGE_SIZE = 100
LISTING_TIMEOUT = 30


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
            rows, total, failed, full_retry = [], None, False, False
            while total is None or len(rows) < total:
                if deadline and time.monotonic() >= deadline:
                    errors.append(f"{label}: deadline reached")
                    break
                payload = get_json(session, f"{BASE}/services/{servlet}", timeout=LISTING_TIMEOUT, params={
                    "start": len(rows), "rows": PAGE_SIZE, "search": "jobsByLocation", "searchstring": "India",
                })
                if payload is None:
                    errors.append(f"{label}: listing request failed at offset {len(rows)}")
                    failed = True
                    break
                if not isinstance(payload, dict) or not isinstance(payload.get("jobsList"), list) or not isinstance(payload.get("totalMatches"), int):
                    errors.append(f"{label}: invalid listing response")
                    failed = True
                    break
                total = min(payload["totalMatches"], MAX_RESULTS_PER_SEARCH)
                if not payload["jobsList"]:
                    # The servlet may not treat `start` as a row offset. Retry once with
                    # one request sized to the reported total before settling for partial.
                    if rows and len(rows) < total and not full_retry:
                        full_retry = True
                        retry = get_json(session, f"{BASE}/services/{servlet}", timeout=LISTING_TIMEOUT, params={
                            "start": 0, "rows": total, "search": "jobsByLocation", "searchstring": "India",
                        })
                        if isinstance(retry, dict) and isinstance(retry.get("jobsList"), list) and len(retry["jobsList"]) > len(rows):
                            rows = list(retry["jobsList"])
                    break
                rows.extend(payload["jobsList"])
            if total is not None and len(rows) < total and not failed:
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
