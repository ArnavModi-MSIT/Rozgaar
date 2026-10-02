"""Flipkart's official linked TurboHire public career feed."""

import json
import time

import requests

from .http_client import get_json, post_json
from .result import CollectionResult
from .standard import strip_html

ORG_ID = "4d757ba0-3d57-448a-b82c-238ed87ac90f"
PORTAL = "https://flipkart.turbohire.co"
API = "https://api.turbohire.co"


def _parse(job):
    locations = job.get("Location") or "[]"
    if isinstance(locations, str):
        locations = json.loads(locations)
    location = "; ".join(item.get("Address", "") for item in locations)
    experience = job.get("Experience") or {}
    parts = [strip_html(job.get("JobDescriptionV2") or job.get("JobDescription") or job.get("JobDescV2") or "", max_chars=None)]
    if experience.get("MinExp") is not None:
        parts.append(f"Minimum experience required: {experience['MinExp']} years.")
    if job.get("Skills"):
        parts.append("Skills: " + ", ".join(job["Skills"]))
    return {
        "company": "flipkart", "source_id": str(job["JobId"]),
        "title": job["JobTitle"], "location": location,
        "url": f"{PORTAL}/job/publicjobs/{job['JobId']}",
        "description": "\n\n".join(parts)[:10000],
    }


def collect(deadline=None):
    errors = []
    jobs = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0", "Origin": PORTAL, "Referer": PORTAL + "/"})
        token = get_json(session, API + "/api/token/noauth")
        if not isinstance(token, dict) or not token.get("access_token"):
            raise RuntimeError("Flipkart: anonymous public access unavailable")
        session.headers["Authorization"] = "Bearer " + token["access_token"]
        data = post_json(session, API + "/api/careerpagev2/filteredjobs", params={"orgId": ORG_ID, "pageType": 0}, json={})
        if not isinstance(data, dict) or not isinstance(data.get("Result"), list):
            raise RuntimeError("Flipkart: public listing response unavailable")
        rows = data["Result"]
        total = data.get("Total")
        if total != len(rows):
            errors.append(f"received {len(rows)} of {total} listings")
        seen = set()
        for row in rows:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("deadline reached")
                break
            jid = row.get("JobId")
            if not jid or jid in seen:
                continue
            seen.add(jid)
            detail = get_json(session, "https://thapi.azurewebsites.net/api/publicjobs", params={"jobId": jid, "fieldVisibility": "true"})
            if not isinstance(detail, dict) or not (detail.get("JobDescriptionV2") or detail.get("JobDescription")):
                errors.append(f"description unavailable for {jid}")
                detail = row
            try:
                jobs.append(_parse(detail))
            except (ValueError, KeyError, TypeError) as exc:
                errors.append(f"invalid posting {jid}: {type(exc).__name__}")
        if len(jobs) != len(rows):
            errors.append(f"normalized {len(jobs)} of {len(rows)} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
