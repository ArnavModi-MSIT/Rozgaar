"""Meta Careers logged-out India office search and public structured descriptions."""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

from .http_client import get_text
from .result import CollectionResult
from .standard import strip_html

BASE = "https://www.metacareers.com"
OFFICES = ["Mumbai, India", "Gurgaon, India", "Bangalore, India", "Hyderabad, India", "New Delhi, India"]
RESULT_QUERY = "CareersJobSearchResultsV2DataQuery"
COUNT_QUERY = "CareersJobSearchHideFiltersBarV2Query"


def _bootstrap(session, deadline):
    html = get_text(session, BASE + "/jobsearch/", params={f"offices[{i}]": office for i, office in enumerate(OFFICES)}) or ""
    match = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', html)
    if not match:
        raise RuntimeError("Meta: public search bootstrap unavailable")
    operations = {}
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.select("script[src]"):
        if deadline is not None and time.monotonic() >= deadline:
            break
        url = script["src"]
        if not url.startswith("https://static.xx.fbcdn.net/"):
            continue
        code = get_text(session, url) or ""
        for name in (RESULT_QUERY, COUNT_QUERY):
            pattern = re.escape(name + '_candidate_portalRelayOperation') + r'"[^\n]{0,100}?\.exports="(\d+)"'
            found = re.search(pattern, code)
            if found:
                operations[name] = found.group(1)
        if len(operations) == 2:
            break
    if RESULT_QUERY not in operations:
        raise RuntimeError("Meta: current public search operation unavailable")
    return match.group(1), operations


def _query(session, token, operation, variables):
    response = session.post(BASE + "/api/graphql/", data={"lsd": token, "doc_id": operation, "variables": json.dumps(variables)}, headers={"X-FB-LSD": token, "Referer": BASE + "/jobsearch/"}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors") or not isinstance(payload.get("data"), dict):
        raise RuntimeError("Meta: public query failed")
    return payload["data"]


def _description(job, deadline):
    if deadline is not None and time.monotonic() >= deadline:
        return ""
    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0"
        html = get_text(session, job["url"]) or ""
    for script in BeautifulSoup(html, "html.parser").select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.get_text())
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting":
            parts = [data.get(field) or "" for field in ("description", "responsibilities", "qualifications")]
            return "\n\n".join(strip_html(part, max_chars=None) for part in parts if part)[:10000]
    return ""


def collect(deadline=None):
    errors = []
    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0"
        token, operations = _bootstrap(session, deadline)
        search = {"offices": OFFICES, "results_per_page": None}
        variables = {"isLoggedIn": False, "viewasUserID": None, "search_input": search}
        result = _query(session, token, operations[RESULT_QUERY], variables).get("job_search_with_featured_jobs_v2")
        if not isinstance(result, dict) or not isinstance(result.get("all_jobs"), list):
            raise RuntimeError("Meta: invalid public listing response")
        # Featured recommendations are outside the filtered result count.
        rows = result["all_jobs"]
        total = None
        if COUNT_QUERY in operations:
            try:
                count = _query(session, token, operations[COUNT_QUERY], {"search_input": search})
                total = count.get("job_search_with_featured_jobs_v2", {}).get("job_count")
            except (requests.RequestException, ValueError, RuntimeError):
                errors.append("reported count unavailable")
        if total is None:
            errors.append("reported total missing")
    jobs = {}
    for row in rows:
        if not row.get("id") or not row.get("title"):
            errors.append("listing missing ID or title")
            continue
        jobs[row["id"]] = {"company": "meta", "source_id": row["id"], "title": row["title"], "location": "; ".join(row.get("locations") or []), "url": f"{BASE}/profile/job_details/{row['id']}", "description": ""}
    if total is not None and len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, description in zip(jobs.values(), pool.map(lambda job: _description(job, deadline), jobs.values())):
            job["description"] = description
    missing = sum(not job["description"] for job in jobs.values())
    if missing:
        errors.append(f"{missing} descriptions unavailable")
    return CollectionResult(jobs.values(), status="partial" if errors else "ok", error="; ".join(errors))
