"""Quadeye's public first-party job feed used by its careers frontend."""
import re
import time
import requests
from backend.fetchers.http_client import get_json
from backend.fetchers.result import CollectionResult
from backend.fetchers.standard import strip_html

BASE = "https://www.quadeye.com"
SESSION = requests.Session()


def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial", error="deadline reached before request")
    data = get_json(SESSION, BASE + "/api/zoho-recruit/job-openings")
    if not isinstance(data, dict) or data.get("success") is not True or not isinstance(data.get("data"), list):
        raise RuntimeError("Quadeye public jobs response unavailable")
    jobs, seen, errors = [], set(), []
    for d in data["data"]:
        if not d.get("id") or not d.get("Posting_Title"):
            errors.append("malformed listing")
            continue
        if str(d["id"]) in seen:
            continue
        seen.add(str(d["id"]))
        title = d["Posting_Title"]
        slug = re.sub(r"-+", "-", re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", title.lower().strip())))
        locations = d.get("Job_Location") or ([d["City"]] if d.get("City") else [])
        if isinstance(locations, str):
            locations = [locations]
        location = "; ".join(locations)
        if d.get("Country"):
            location += ", " + d["Country"]
        description = strip_html(d.get("Job_Description", ""), max_chars=None)[:12000]
        if not description:
            errors.append(f"description unavailable: {d['id']}")
        jobs.append({"company": "quadeye", "source_id": str(d["id"]), "title": title,
                     "location": location, "description": description,
                     "url": f"{BASE}/jobs/{d['id']}/{slug}?source=CareerSite"})
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
