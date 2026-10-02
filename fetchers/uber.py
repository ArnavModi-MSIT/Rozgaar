"""Uber's public India job search, including descriptions and pagination."""

import time
from urllib.parse import urljoin

import requests

from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

BASE = "https://jobs.uber.com"
MAX_PAGES = 1000


def _parse(raw):
    links = raw.get("Urls") or []
    link = next((item for item in links if item.get("IsDefault")), links[0] if links else {})
    description = "\n\n".join(strip_html(raw.get(field) or "", max_chars=None) for field in ("Description", "AdditionalDescription1", "Summary") if raw.get(field))
    return {"company": "uber", "source_id": str(raw["Id"]), "title": raw["Title"], "location": "; ".join(loc.get("Address") or ", ".join(loc.get(field) or "" for field in ("City", "Region", "Country")) for loc in raw.get("Locations") or []), "url": urljoin(BASE, link.get("Url") or f"/en/jobs/{raw['Id']}/"), "description": description[:10000]}


def collect(deadline=None):
    jobs = {}
    errors = []
    total = None
    with requests.Session() as session:
        for page in range(1, MAX_PAGES + 1):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("deadline reached")
                break
            data = get_json(session, BASE + "/api/jobs/search/", params={"countries": "India", "page": page})
            if not isinstance(data, dict) or not isinstance(data.get("jobs"), list) or data.get("page") != page:
                if page == 1:
                    raise RuntimeError("Uber: first search page unavailable")
                errors.append(f"page {page} unavailable")
                break
            total = data.get("totalJobs")
            pages = data.get("totalPages")
            if not isinstance(total, int) or not isinstance(pages, int):
                errors.append("reported totals missing")
                break
            before = len(jobs)
            for raw in data["jobs"]:
                try:
                    job = _parse(raw)
                    jobs[job["source_id"]] = job
                except (KeyError, TypeError, ValueError):
                    errors.append(f"invalid listing on page {page}")
            if page >= pages:
                break
            if len(jobs) == before:
                errors.append(f"page {page} returned no new listings")
                break
            time.sleep(0.3)
        else:
            errors.append("pagination safety limit reached")
    if total is not None and len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")
    missing = sum(not job["description"] for job in jobs.values())
    if missing:
        errors.append(f"{missing} descriptions unavailable")
    return CollectionResult(jobs.values(), status="partial" if errors else "ok", error="; ".join(errors))
