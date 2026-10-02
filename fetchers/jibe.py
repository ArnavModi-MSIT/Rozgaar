"""Shared public Jibe India search with full descriptions and partial status."""
import time
from urllib.parse import urlencode
from fetchers import icims
from fetchers.result import CollectionResult
from fetchers.standard import strip_html

def collect(company, domain, path, deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    for page in range(1, 501):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("deadline reached")
            break
        data = icims._fetch_page(domain, page, "/api/jobs", "country=India")
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            if not jobs:
                raise RuntimeError("Public Jibe jobs response unavailable or invalid")
            errors.append(f"page {page} failed")
            break
        if isinstance(data.get("totalCount"), int):
            total = data["totalCount"]
        added = 0
        for entry in data["jobs"]:
            d = entry.get("data", entry)
            req_id = d.get("req_id") or d.get("slug")
            if not req_id or not d.get("title"):
                errors.append("malformed job record")
                continue
            if str(req_id) in seen:
                continue
            seen.add(str(req_id))
            description = strip_html(d.get("description", ""), max_chars=None)[:10000]
            if not description:
                errors.append(f"description unavailable: {req_id}")
            location = ", ".join(str(d[k]) for k in ("city", "state", "country") if d.get(k)) or d.get("location_name", "")
            jobs.append({"company": company, "source_id": str(req_id), "title": d["title"],
                         "location": location, "description": description,
                         "url": f"https://{domain}{path}/{d.get('slug') or req_id}"})
            added += 1
        if total is not None and len(jobs) >= total:
            break
        if not added:
            break
    else:
        errors.append("page limit reached")
    if total is None:
        errors.append("listing total unavailable")
    elif len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
