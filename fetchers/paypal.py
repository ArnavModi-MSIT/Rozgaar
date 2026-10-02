"""PayPal's public Workday India listings and job descriptions."""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests

from fetchers.http_client import get_json, post_json
from fetchers.result import CollectionResult
from fetchers.standard import strip_html

BASE = "https://paypal.wd1.myworkdayjobs.com"
SITE = "jobs"
SEARCH_URL = f"{BASE}/wday/cxs/paypal/{SITE}/jobs"
REFERER = f"{BASE}/en-US/{SITE}"
PAGE_SIZE = 20
MAX_PAGES = 100
DETAIL_WORKERS = 3


def _request_page(session, offset, facets):
    return post_json(session, SEARCH_URL, json={
        "appliedFacets": facets, "limit": PAGE_SIZE,
        "offset": offset, "searchText": "",
    }, headers={"Referer": REFERER})


def _india_location_ids(data):
    for group in data.get("facets") or []:
        for facet in group.get("values") or []:
            if facet.get("facetParameter") == "locations":
                return [item["id"] for item in facet.get("values") or []
                        if item.get("id") and re.search(r"\bIndia\b", item.get("descriptor", ""), re.I)]
    return []


def _job(row):
    path = row.get("externalPath") or ""
    bullets = row.get("bulletFields") or []
    source_id = bullets[0] if bullets and re.fullmatch(r"R\d+", str(bullets[0])) else ""
    if not source_id:
        found = re.search(r"(R\d+)(?:$|[/?])", path)
        source_id = found.group(1) if found else ""
    if not source_id or not path.startswith("/job/"):
        return None
    location = row.get("locationsText") or "India"
    if "India" not in location and "Locations" in location:
        location += ", India"  # the location facet already scoped this posting to India
    return {
        "company": "paypal", "source_id": source_id,
        "title": row.get("title") or "Untitled job", "location": location,
        "url": urljoin(REFERER + "/", path.lstrip("/")),
        "description": "", "_path": path,
    }


def _description(job):
    with requests.Session() as session:
        data = get_json(session, f"{BASE}/wday/cxs/paypal/{SITE}{job['_path']}",
                        headers={"Referer": REFERER})
    html = (data.get("jobPostingInfo") or {}).get("jobDescription") if isinstance(data, dict) else None
    return strip_html(html, max_chars=None)[:6000] if html else ""


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    with requests.Session() as session:
        first = _request_page(session, 0, {})
        if not isinstance(first, dict):
            raise RuntimeError("PayPal Workday: initial listing request failed")
        ids = _india_location_ids(first)
        if not ids:
            raise RuntimeError("PayPal Workday: India location facet missing")
        facets = {"locations": ids}
        total = None
        for page in range(MAX_PAGES):
            if deadline and time.monotonic() >= deadline:
                errors.append(f"deadline before listing page {page + 1}")
                break
            data = _request_page(session, page * PAGE_SIZE, facets)
            if not isinstance(data, dict) or not isinstance(data.get("jobPostings"), list) or not isinstance(data.get("total"), int):
                errors.append(f"listing page {page + 1} failed")
                break
            if total is None:
                total = data["total"]
            rows = data["jobPostings"]
            if not rows and page * PAGE_SIZE < total:
                errors.append(f"listing page {page + 1} empty before reported total {total}")
                break
            for row in rows:
                job = _job(row)
                if job is None:
                    errors.append(f"invalid job on listing page {page + 1}")
                elif job["source_id"] not in seen:
                    seen.add(job["source_id"])
                    jobs.append(job)
            if (page + 1) * PAGE_SIZE >= total:
                break
            if len(rows) < PAGE_SIZE:
                errors.append(f"short listing page {page + 1} before reported total {total}")
                break
            time.sleep(0.3)
        else:
            errors.append(f"exceeded {MAX_PAGES} listing pages")

    if jobs and not (deadline and time.monotonic() >= deadline):
        with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
            futures = {pool.submit(_description, job): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                try:
                    job["description"] = future.result()
                except Exception:
                    pass
                if not job["description"]:
                    errors.append(f"description unavailable for {job['source_id']}")
    elif jobs:
        errors.append("deadline before descriptions")
    for job in jobs:
        job.pop("_path", None)
    if errors and not jobs:
        raise RuntimeError("PayPal Workday: " + "; ".join(errors[:5]))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))
