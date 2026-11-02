"""Public India listings from TalentBrew (Radancy) career sites, with full job-page descriptions.

cfg keys: company, host (careers site), org_id (TalentBrew OrganizationIds, e.g. 44408 for
Synopsys). Uses the site's own `/search-jobs/results` endpoint with the India location
(geoname 1269750), the same request the site's pager makes. Verified on Synopsys on
2 November 2026: 201 unique India postings, descriptions in `.ats-description`.
Other TalentBrew tenants differ in markup and filters; confirm each before registering it.
"""
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .http_client import get_json, get_text
from .result import CollectionResult
from .standard import _expansion_location

PAGE_SIZE = 15
MAX_PAGES = 100


def _params(org_id, page):
    return {"ActiveFacetID": 0, "CurrentPage": page, "RecordsPerPage": PAGE_SIZE, "TotalContentResults": 2,
            "Distance": 50, "RadiusUnitType": 0, "Keywords": "", "Location": "India",
            "Latitude": "22.00000", "Longitude": "79.00000", "ShowRadius": "False", "IsPagination": "False",
            "CustomFacetName": "", "FacetTerm": "", "FacetType": 0,
            "SearchResultsModuleName": "Search Results", "SearchFiltersModuleName": "Search Filters",
            "SortCriteria": 0, "SortDirection": 0, "SearchType": 1, "LocationType": 2,
            "LocationPath": 1269750, "OrganizationIds": org_id, "PostalCode": "", "ResultsType": 0,
            "fc": "", "fl": "", "fcf": "", "afc": "", "afl": "", "afcf": "", "TotalContentPages": 1}


def parse_results(html, root):
    """Jobs on one results page; foreign or unknown locations are dropped, never guessed."""
    soup = BeautifulSoup(html or "", "html.parser")
    jobs, skipped = [], 0
    for link in soup.select("a[data-job-id]"):
        title = link.select_one("h2, h3")
        location = link.select_one(".job-location")
        text = location.get_text(" ", strip=True) if location else ""
        if title is None or not link.get("href"):
            raise ValueError("listing title or link unavailable")
        # Positive India evidence only: "India" in the text, or an anchored Indian city/state label
        # ("Bengaluru, Karnataka"), which gets ", India" appended. Remote or foreign rows are dropped.
        text = _expansion_location(text)
        if not text:
            skipped += 1
            continue
        jobs.append({"source_id": link["data-job-id"], "title": title.get_text(" ", strip=True),
                     "location": text, "url": urljoin(root, link["href"]), "description": ""})
    return jobs, skipped


def fetch(cfg, deadline=None):
    host, org_id, company = cfg["host"], cfg["org_id"], cfg["company"]
    root = "https://" + host
    jobs, seen, errors = [], set(), []
    with requests.Session() as session:
        session.headers.update({"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0"})
        for page in range(1, MAX_PAGES + 1):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("listing deadline reached")
                break
            data = get_json(session, root + "/search-jobs/results", params=_params(org_id, page))
            if not isinstance(data, dict) or not isinstance(data.get("results"), str):
                if not jobs:
                    raise RuntimeError(f"TalentBrew {host}: listing unavailable")
                errors.append(f"page {page} unavailable")
                break
            if "data-job-id" not in data["results"]:
                break  # an empty page ends the listing
            try:
                batch, _ = parse_results(data["results"], root)
            except ValueError as exc:
                if not jobs:
                    raise RuntimeError(f"TalentBrew {host}: {exc}") from exc
                errors.append(str(exc))
                break
            fresh = [job for job in batch if job["source_id"] not in seen]
            for job in fresh:
                seen.add(job["source_id"])
                jobs.append(job)
            if batch and not fresh:
                errors.append("repeated listing page")
                break
            time.sleep(0.2)
        else:
            errors.append("listing page limit reached")

    def detail(job):
        if deadline is not None and time.monotonic() >= deadline:
            return ""
        if urlsplit(job["url"]).hostname != host:
            return ""
        with requests.Session() as session:
            html = get_text(session, job["url"])
        node = BeautifulSoup(html or "", "html.parser").select_one(".ats-description")
        return node.get_text("\n", strip=True) if node else ""

    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, text in zip(jobs, pool.map(detail, jobs)):
            job["description"] = text
            job["company"] = company
            if not text:
                errors.append("description unavailable: " + job["source_id"])
    if not jobs:
        raise RuntimeError(f"TalentBrew {host}: no India listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))
