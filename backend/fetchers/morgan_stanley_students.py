"""Morgan Stanley's separate public Students & Graduates search feed."""
import time
import re
import requests
from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

BASE = "https://www.morganstanley.com"
SEARCH_URL = BASE + "/careers/career-opportunities-search?opportunity=sg"
ENDPOINT = BASE + "/web/career_services/webapp/service/careerservice/resultset.json"


def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        raise RuntimeError("Morgan Stanley students: deadline before request")
    with requests.Session() as session:
        session.headers["User-Agent"] = "Mozilla/5.0"
        data = get_json(session, ENDPOINT, params={"opportunity": "sg", "lang": "en"})
    if not isinstance(data, dict) or not isinstance(data.get("resultSet"), list):
        raise RuntimeError("Morgan Stanley students: invalid search response")
    rows = data["resultSet"]
    total = data.get("totalResults")
    errors = []
    if not isinstance(total, int) or total != len(rows):
        errors.append(f"received {len(rows)} rows; reported total {total}")
    jobs = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("invalid listing")
            continue
        # Collect only explicitly India-based student programs from this global feed.
        location = row.get("location") or ""
        country = row.get("country") or ""
        if not re.search(r"\bindia\b", location + " " + country, re.I):
            continue
        identifier = str(row.get("jobNumber") or "")
        title = row.get("jobTitle") or ""
        if not identifier or not title:
            errors.append("India listing missing job number or title")
            continue
        description = strip_html(row.get("jobHtmlDescription") or row.get("jobDescription") or "", max_chars=None)
        qualifications = strip_html(row.get("qualification") or "", max_chars=None)
        if qualifications and qualifications not in description:
            description += "\n\nQualifications\n" + qualifications
        if not description.strip():
            errors.append(f"description missing for {identifier}")
        jobs[identifier] = {"company": "morganstanley", "source_id": identifier,
            "title": title, "location": location or "India",
            "url": BASE + "/careers/students-graduates/opportunities/" + identifier,
            "description": description}
    return CollectionResult(jobs.values(), status="partial" if errors else "ok", error="; ".join(errors))
