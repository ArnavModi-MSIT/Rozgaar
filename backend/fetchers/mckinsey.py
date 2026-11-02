"""McKinsey's public job search API for postings open in India, with descriptions in the list.

GET https://gateway.mckinsey.com/apigw-x0cceuow60/v1/api/jobs/search?pageSize=20&start=N&countries=India&lang=en
(the request the careers page's "Load More" makes; `start` is the 1-based page). Each doc carries
parallel `cities` and `countries` arrays, so a global role (an associate internship lists ~87 cities)
is kept with its India cities only. Verified on 2 November 2026: 49 postings over 3 pages.
Compensation fields are deliberately ignored: they are in US dollars for other offices.
"""
import time

import requests

from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

API = "https://gateway.mckinsey.com/apigw-x0cceuow60/v1/api/jobs/search"
PAGE_SIZE = 20
MAX_PAGES = 30
SECTIONS = ("whatYouWillDo", "whoYouWillWorkWith", "yourBackground")


def parse_doc(doc):
    job_id, title, slug = str(doc.get("jobID") or ""), (doc.get("title") or "").strip(), doc.get("friendlyURL") or ""
    if not job_id or not title or not slug or "/" in slug:
        raise ValueError("listing identity unavailable")
    cities, countries = doc.get("cities") or [], doc.get("countries") or []
    if len(cities) != len(countries):
        raise ValueError("cities and countries are not aligned: " + job_id)
    india = list(dict.fromkeys(c for c, k in zip(cities, countries) if k == "India" and c))
    if not india:
        return None
    parts = [strip_html(doc.get(key) or "", max_chars=None).strip() for key in SECTIONS]
    return {"source_id": job_id, "title": title, "location": "; ".join(f"{c}, India" for c in india),
            "url": f"https://www.mckinsey.com/careers/search-jobs/jobs/{slug}",
            "description": "\n\n".join(part for part in parts if part)}


def fetch(cfg, deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for page in range(1, MAX_PAGES + 1):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("listing deadline reached")
                break
            data = get_json(session, API, params={"pageSize": PAGE_SIZE, "start": page, "countries": "India", "lang": "en"})
            if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
                if not jobs:
                    raise RuntimeError("McKinsey: listing unavailable")
                errors.append(f"page {page} unavailable")
                break
            total = data.get("numFound", total)
            docs = data["docs"]
            if not docs:
                break
            fresh = 0
            for doc in docs:
                try:
                    job = parse_doc(doc)
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
            if not fresh and docs:
                errors.append("repeated or foreign-only listing page")
                break
            if len(docs) < PAGE_SIZE:
                break
            time.sleep(0.2)
        else:
            errors.append("listing page limit reached")
    if not jobs:
        raise RuntimeError("McKinsey: no India listings")
    if isinstance(total, int) and len(jobs) < total:
        errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(dict.fromkeys(errors))[:1200])
