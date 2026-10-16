"""Published vacancies from Gem's logged-out job-board GraphQL endpoint."""
import re
import time
from urllib.parse import quote

import requests

from .http_client import post_json
from .result import CollectionResult
from .standard import strip_html


ENDPOINT = "https://jobs.gem.com/api/public/graphql"
LIST_QUERY = """query JobBoardList($boardId: String!) {
  oatsExternalJobPostings(boardId: $boardId) {
    jobPostings { id extId title locations { name city isoCountry isRemote } }
  }
  jobBoardExternal(vanityUrlPath: $boardId) { id teamDisplayName pageTitle }
}"""
DETAIL_QUERY = """query ExternalJobPosting($boardId: String!, $extId: String!) {
  oatsExternalJobPosting(boardId: $boardId, extId: $extId) {
    id extId title descriptionHtml isUnlistedExternally
    locations { name city isoCountry isRemote }
    jobPostSectionHtml { introHtml outroHtml }
    compensationHtml
  }
}"""


def _expired(deadline):
    return deadline is not None and time.monotonic() >= deadline


def _india_locations(locations):
    result = []
    for loc in locations if isinstance(locations, list) else []:
        if not isinstance(loc, dict) or str(loc.get("isoCountry", "")).upper() not in {"IN", "IND", "INDIA"}:
            continue
        label = loc.get("name") or loc.get("city") or "India"
        if not re.search(r"\bIndia\b", label, re.I):
            label += ", India"
        if label not in result:
            result.append(label)
    return "; ".join(result)


def fetch(cfg, deadline=None):
    if _expired(deadline):
        raise RuntimeError("Gem listing deadline reached")
    jobs, errors, seen = [], [], set()
    with requests.Session() as session:
        payload = post_json(session, ENDPOINT, json={"query": LIST_QUERY, "variables": {"boardId": cfg["board"]}})
        data = payload.get("data") if isinstance(payload, dict) and not payload.get("errors") else None
        board = data.get("jobBoardExternal") if isinstance(data, dict) else None
        listing = data.get("oatsExternalJobPostings") if isinstance(data, dict) else None
        if not isinstance(board, dict) or board.get("teamDisplayName") != cfg["expected_team"]:
            raise RuntimeError("Gem board unavailable or employer identity mismatch")
        if not isinstance(listing, dict) or not isinstance(listing.get("jobPostings"), list):
            raise RuntimeError("Gem listing unavailable")
        for row in listing["jobPostings"]:
            if not isinstance(row, dict) or not all(row.get(k) for k in ("id", "extId", "title")):
                errors.append("malformed Gem listing")
                continue
            sid = row["extId"]
            if sid in seen:
                errors.append("duplicate Gem listing: " + sid)
                continue
            seen.add(sid)
            location = _india_locations(row.get("locations"))
            if not location:
                continue
            # This explicit form is for future interest, not a current vacancy.
            if re.fullmatch(r"(?:join (?:our|the) )?talent community[!.\s]*", row["title"], re.I):
                continue
            job = dict(company=cfg["company"], source_id=sid, title=row["title"].strip(),
                       location=location, url="https://jobs.gem.com/" + quote(cfg["board"], safe="") + "/" + quote(sid, safe=""),
                       description="")
            if _expired(deadline):
                errors.append("description deadline reached: " + sid)
                jobs.append(job)
                continue
            payload = post_json(session, ENDPOINT, json={"query": DETAIL_QUERY, "variables": {"boardId": cfg["board"], "extId": sid}})
            data = payload.get("data") if isinstance(payload, dict) else None
            detail = data.get("oatsExternalJobPosting") if isinstance(data, dict) else None
            if isinstance(payload, dict) and payload.get("errors"):
                errors.append("Gem detail query incomplete: " + sid)
                detail = None
            if (not isinstance(detail, dict) or detail.get("id") != row["id"]
                    or detail.get("extId") != sid or detail.get("title", "").strip() != job["title"]):
                errors.append("detail unavailable or identity mismatch: " + sid)
                jobs.append(job)
                continue
            if detail.get("isUnlistedExternally") is not False:
                errors.append("detail visibility unavailable or no longer public: " + sid)
                continue
            location = _india_locations(detail.get("locations"))
            if not location:
                errors.append("detail no longer lists India: " + sid)
                continue
            job["location"] = location
            sections = detail.get("jobPostSectionHtml") or {}
            body = detail.get("descriptionHtml")
            if not isinstance(body, str) or not strip_html(body, max_chars=None):
                errors.append("description unavailable: " + sid)
            else:
                parts = [sections.get("introHtml"), body, sections.get("outroHtml"), detail.get("compensationHtml")]
                job["description"] = "\n".join(strip_html(part, max_chars=None) for part in parts if isinstance(part, str) and part.strip())
            jobs.append(job)
    if errors and not jobs:
        raise RuntimeError("; ".join(errors[:8]))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:8]))
