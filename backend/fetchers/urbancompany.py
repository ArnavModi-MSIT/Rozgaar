"""Urban Company's public job list (the request its careers page makes), descriptions included.

POST https://www.urbanclap.com/api/v2/platform-gateway/getAllJobs with an empty JSON object returns
{"jobs": [{job_id, job_code, job_title, job_description, location[], apply_url, ...}]}.
Verified on 2 November 2026: 10 postings, all India, 10 with descriptions. GET is not supported.
"""
import requests

from .http_client import post_json
from .result import CollectionResult
from .standard import strip_html

API = "https://www.urbanclap.com/api/v2/platform-gateway/getAllJobs"
APPLY_HOST = "urbancompany.turbohire.co"


def parse_row(row):
    job_id, title = str(row.get("job_id") or ""), (row.get("job_title") or "").strip()
    url = row.get("apply_url") or ""
    if not job_id or not title or not url.startswith(f"https://{APPLY_HOST}/"):
        raise ValueError("listing identity unavailable")
    places = [" ".join(str(p).split()) for p in row.get("location") or [] if str(p).strip()]
    india = [p for p in places if p.lower().endswith("india")]
    if not india:
        return None  # no positive India evidence; never guess
    text = strip_html(row.get("job_description") or "", max_chars=None).strip()
    return {"source_id": job_id, "title": title, "location": "; ".join(dict.fromkeys(india)), "url": url, "description": text}


def fetch(cfg, deadline=None):
    with requests.Session() as session:
        data = post_json(session, API, json={})
    rows = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("Urban Company: listing unavailable")
    jobs, seen, errors = [], set(), []
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
        if not job["description"]:
            errors.append("description unavailable: " + job["source_id"])
    if not jobs:
        raise RuntimeError("Urban Company: no India listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))
