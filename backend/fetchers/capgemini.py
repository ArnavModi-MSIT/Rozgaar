"""Capgemini India listings from its public job-search JSON API, with descriptions in the list.

Endpoint: https://cg-jobstream-api.azurewebsites.net/api/job-search?page=N&size=100&country_code=in-en
(the same request the Capgemini India job-search page makes). Verified on 2 November 2026:
635 total, 634 unique ids, every row `country_code` "en-in", descriptions present.
"""
import time

import requests

from .http_client import get_json
from .result import CollectionResult

API = "https://cg-jobstream-api.azurewebsites.net/api/job-search"
PAGE_SIZE = 100
MAX_PAGES = 50


def _location(value):
    text = " ".join(str(value or "").split())
    if not text:
        return "India"
    return text if "india" in text.lower() else text + ", India"


def parse_row(row):
    job_id, title = str(row.get("id") or ""), (row.get("title") or "").strip()
    url = row.get("apply_job_url") or ""
    if not job_id or not title or not url.startswith("https://careers.capgemini.com/"):
        raise ValueError("listing identity unavailable")
    if str(row.get("country_code", "")).lower() != "en-in":
        return None  # the India feed should only hold en-in; anything else is not claimed
    text = (row.get("description_stripped") or "").strip()
    if text and row.get("experience_level"):  # never let metadata alone pass as a description
        text += "\nExperience level: " + str(row["experience_level"])
    return {"source_id": job_id, "title": title, "location": _location(row.get("location")), "url": url,
            "description": text.strip()}


def fetch(cfg, deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for page in range(1, MAX_PAGES + 1):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("listing deadline reached")
                break
            data = get_json(session, API, params={"page": page, "size": PAGE_SIZE, "country_code": "in-en"})
            if not isinstance(data, dict) or not isinstance(data.get("data"), list) or not isinstance(data.get("total"), int):
                if not jobs:
                    raise RuntimeError("Capgemini: listing unavailable")
                errors.append(f"page {page} unavailable")
                break
            total = data["total"]
            rows = data["data"]
            if not rows:
                break
            fresh = 0
            for row in rows:
                try:
                    job = parse_row(row)
                except (ValueError, AttributeError) as exc:
                    errors.append(str(exc))
                    continue
                if job is None or job["source_id"] in seen:
                    continue
                seen.add(job["source_id"])
                job["company"] = cfg["company"]
                jobs.append(job)
                fresh += 1
                if not job["description"]:
                    errors.append("description unavailable: " + job["source_id"])
            if not fresh:
                errors.append("repeated or empty listing page")
                break
            if len(seen) >= total or len(rows) < PAGE_SIZE:
                break
            time.sleep(0.2)
        else:
            errors.append("listing page limit reached")
    if not jobs:
        raise RuntimeError("Capgemini: no India listings")
    if total is not None and len(jobs) < total - 5:
        errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(dict.fromkeys(errors))[:1200])
