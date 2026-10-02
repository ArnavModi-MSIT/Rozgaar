"""Public D. E. Shaw India jobs embedded in the official careers page."""
import json
import time
import requests
from bs4 import BeautifulSoup
from fetchers.http_client import get_text
from fetchers.result import CollectionResult
from fetchers.standard import strip_html

BASE = "https://www.deshawindia.com"
SESSION = requests.Session()


def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial", error="deadline reached before request")
    html = get_text(SESSION, BASE + "/careers")
    if not html:
        raise RuntimeError("D. E. Shaw India careers unavailable")
    node = BeautifulSoup(html, "html.parser").select_one("#__NEXT_DATA__")
    if not node:
        raise RuntimeError("D. E. Shaw India job payload missing")
    props = json.loads(node.string)["props"]["pageProps"]
    if props.get("jobsFetchingError") or not isinstance(props.get("regularJobs"), list):
        raise RuntimeError("D. E. Shaw India job payload failed")
    jobs, seen, errors = [], set(), []
    for entry in props["regularJobs"]:
        d = entry.get("data", {})
        meta = d.get("jobMetadata") or {}
        if meta.get("isExploratory") or d.get("activeOnJobsListing") is False:
            continue
        if not d.get("id") or not d.get("jobUrl"):
            errors.append("malformed listing")
            continue
        if str(d["id"]) in seen:
            continue
        seen.add(str(d["id"]))
        sections = d.get("jobDescription") or {}
        parts = []
        for key in ("websiteDescription", "responsibilities", "peopleWeAreLookingFor"):
            value = sections.get(key + "Html") or sections.get(key)
            if isinstance(value, list):
                value = "\n".join(str(v) for v in value)
            if value:
                parts.append(strip_html(value, max_chars=None))
        description = "\n\n".join(parts)[:12000]
        if not description:
            errors.append(f"description unavailable: {d['id']}")
        cities = [v["name"] for v in meta.get("jobLocations", []) if v.get("name")]
        jobs.append({"company": "deshaw", "source_id": str(d["id"]),
                     "title": d.get("displayName") or entry.get("displayName", ""),
                     "location": "; ".join(cities) + (", India" if cities else ""),
                     "url": BASE + "/careers/" + d["jobUrl"].lower(), "description": description})
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
