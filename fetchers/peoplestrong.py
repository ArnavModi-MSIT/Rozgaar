"""Public PeopleStrong vacancies; no candidate or application endpoints."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlsplit

import requests

from .http_client import get_json, post_json
from .result import CollectionResult
from .standard import strip_html


def _expired(deadline):
    return deadline is not None and time.monotonic() >= deadline


def _india_location(value):
    # The source supplies a country-first hierarchy, not a city-only label.
    if not isinstance(value, str):
        return ""
    parts = [part.strip() for part in value.split(">") if part.strip()]
    return ", ".join(reversed(parts)) if parts and parts[0].casefold() == "india" else ""


def fetch(cfg, deadline=None):
    base = "https://" + cfg["host"]
    api = base + "/api/cp/rest/altone/cp/"
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for offset in range(0, 10000, 20):
            if _expired(deadline):
                errors.append("listing deadline reached")
                break
            data = post_json(session, api + "jobs/v1", params={"offset": offset, "limit": 20}, json={})
            if not isinstance(data, dict) or not isinstance(data.get("response"), list):
                errors.append("PeopleStrong listing unavailable")
                break
            count = data.get("totalRecords")
            if type(count) is not int or count < 0:
                errors.append("listing total unavailable")
                break
            if total is not None and count != total:
                errors.append("listing total changed")
            total = count
            added = 0
            for row in data["response"]:
                if not isinstance(row, dict) or not row.get("jobCode"):
                    errors.append("listing ID missing")
                    continue
                sid = str(row["jobCode"])
                if sid in seen:
                    continue
                seen.add(sid)
                added += 1
                location = _india_location(row.get("locationHierarchyComplete"))
                if not location:
                    continue
                path = urlsplit(row.get("jobDetailUrl") or "")
                if (path.hostname != cfg["host"] or not path.path.startswith("/job/detail/")
                        or not row.get("jobTitle")):
                    errors.append("malformed India listing: " + sid)
                    continue
                jobs.append(dict(company=cfg["company"], source_id=sid, title=row["jobTitle"],
                                 location=location, url=base + path.path, description=""))
            if len(seen) >= total:
                break
            if not added:
                errors.append("empty or repeated listing page")
                break
        else:
            errors.append("page limit reached")
    if total is None or len(seen) != total:
        errors.append(f"received {len(seen)} of {total} listings")

    def enrich(job):
        if _expired(deadline):
            return "description deadline reached: " + job["source_id"]
        token = job["url"].rsplit("/", 1)[-1]
        with requests.Session() as session:
            data = get_json(session, api + "job/" + quote(token, safe="") + "/v2", params={
                # 'descriprion' is the public frontend's actual parameter spelling.
                "part": "basic,organisational,descriprion,workflow,skill,qualification,certification,language",
                "isReqId": "false"})
        detail = data.get("response") if isinstance(data, dict) else None
        if not isinstance(detail, dict):
            return "description unavailable: " + job["source_id"]
        if (detail.get("requisitionCode") != job["source_id"]
                or detail.get("jobTitle") != job["title"]):
            return "detail identity mismatch: " + job["source_id"]
        location = _india_location(detail.get("locationHierarchyComplete"))
        if not location:
            job["_exclude"] = True
            return "detail country is not India: " + job["source_id"]
        job["location"] = location
        html = detail.get("jobDescription")
        text = strip_html(html, max_chars=None) if isinstance(html, str) else ""
        if not text:
            return "description unavailable: " + job["source_id"]
        minimum = str(detail.get("minimumExp", ""))
        maximum = str(detail.get("maximumExp", ""))
        if re.fullmatch(r"\d+(?:\.\d+)?", minimum):
            span = minimum + ("-" + maximum if re.fullmatch(r"\d+(?:\.\d+)?", maximum) else "+")
            text += "\nRequired experience: " + span + " years of experience."
        job["description"] = text
        return ""

    with ThreadPoolExecutor(max_workers=4) as pool:
        for error in pool.map(enrich, jobs):
            if error:
                errors.append(error)
    jobs = [job for job in jobs if not job.pop("_exclude", False)]
    if errors and not jobs:
        raise RuntimeError("; ".join(errors[:8]))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:8]))
