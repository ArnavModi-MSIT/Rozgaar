"""Millennium's public legacy Eightfold India search (no authentication)."""
import time
import requests
from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

def collect(deadline=None):
    jobs, errors, seen, total = [], [], set(), None
    with requests.Session() as session:
        for start in range(0, 1000, 10):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("deadline reached"); break
            data = get_json(session, "https://career.mlp.com/api/apply/v2/jobs", params={"domain":"mlp.com", "location":"India", "start":start, "num":10})
            if not isinstance(data, dict) or not isinstance(data.get("positions"), list):
                if not jobs: raise RuntimeError("Millennium public search unavailable")
                errors.append("listing request failed"); break
            if total is None: total = data.get("count")
            fresh = 0
            for row in data["positions"]:
                sid = str(row.get("id") or "")
                if not sid or sid in seen: continue
                seen.add(sid); fresh += 1
                jobs.append({"company":"millennium", "source_id":sid, "title":row.get("name", ""), "location":"; ".join(row.get("locations") or [row.get("location", "")]), "url":row.get("canonicalPositionUrl") or f"https://career.mlp.com/careers/job/{sid}", "description":strip_html(row.get("job_description") or "") or "Department: " + row.get("department", "")})
            if total is not None and len(jobs) >= total: break
            if not fresh: break
    if total is None or len(jobs) != total: errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
