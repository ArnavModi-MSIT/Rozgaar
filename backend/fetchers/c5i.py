"""C5i's public India city tabs and public job-description pages."""
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

from .http_client import get_text, post_json
from .result import CollectionResult
from .standard import strip_html


BASE = "https://www.c5i.ai"


def _session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": BASE + "/careers/"})
    return session


def _expired(deadline):
    return deadline is not None and time.monotonic() >= deadline


def fetch(cfg, deadline=None):
    if _expired(deadline):
        raise RuntimeError("C5i listing deadline reached")
    jobs, errors, rows = {}, [], {}
    with _session() as session:
        html = get_text(session, BASE + "/careers/")
        if not html:
            raise RuntimeError("C5i careers page unavailable")
        soup = BeautifulSoup(html, "html.parser")
        block = soup.select_one('.country-block[data-country="india"]')
        cities = list(dict.fromkeys(n["data-city"] for n in block.select("[data-city]") if n["data-city"])) if block else []
        nonce = re.search(r'const\s+nonce\s*=\s*[\"\']([^\"\']+)', html)
        if not cities or not nonce:
            raise RuntimeError("C5i India cities or public listing nonce unavailable")
        for city in cities:
            if _expired(deadline):
                errors.append("city listing deadline reached: " + city)
                break
            payload = {"action": "c5i_jobs_by_city", "nonce": nonce[1], "city": city}
            data = post_json(session, BASE + "/wp-admin/admin-ajax.php",
                             files={k: (None, v) for k, v in payload.items()})
            wrapped = data.get("data") if isinstance(data, dict) and data.get("success") is True else None
            body = wrapped.get("data") if isinstance(wrapped, dict) and wrapped.get("code") == 200 else None
            if not isinstance(body, dict) or not isinstance(body.get("careersJobsList"), list):
                errors.append("city listing unavailable: " + city)
                continue
            listed = body["careersJobsList"]
            ids = set()
            for row in listed:
                if not isinstance(row, dict) or not re.fullmatch(r"\d+", str(row.get("requisitionId", ""))):
                    errors.append("listing ID missing: " + city)
                    continue
                sid = str(row["requisitionId"])
                ids.add(sid)
                title = row.get("requisitionTitle") or row.get("designation")
                if not title:
                    errors.append("title missing: " + sid)
                    continue
                if sid in jobs:
                    if jobs[sid]["title"] != title:
                        errors.append("conflicting listing title: " + sid)
                    locations = jobs[sid]["location"].split("; ")
                    if city + ", India" not in locations:
                        jobs[sid]["location"] += "; " + city + ", India"
                    continue
                rows[sid] = row
                jobs[sid] = dict(company=cfg["company"], source_id=sid, title=title,
                                 location=city + ", India", url=BASE + "/career-apply/?job-id=" + sid,
                                 description="")
            if type(body.get("count")) is not int or body["count"] != len(ids):
                errors.append("city listing count mismatch: " + city)
            if body.get("hasNext") is not False:
                errors.append("additional city pages not retrieved: " + city)

    def enrich(job):
        if _expired(deadline):
            return "description deadline reached: " + job["source_id"]
        with _session() as session:
            html = get_text(session, job["url"])
        soup = BeautifulSoup(html or "", "html.parser")
        sid = soup.select_one('input[name="requisitionId"]')
        title = soup.select_one(".job-details .heading_container h2")
        body = soup.select_one(".job-details .job-description")
        if sid is None or sid.get("value") != job["source_id"] or title is None or title.get_text(" ", strip=True) != job["title"]:
            return "detail identity unavailable or mismatched: " + job["source_id"]
        text = strip_html(str(body), max_chars=None) if body else ""
        if not text or text.strip().casefold() == "job description":
            return "description unavailable: " + job["source_id"]
        row = rows[job["source_id"]]
        minimum, maximum = row.get("yrsOfExpMin"), row.get("yrsOfExpMax")
        # A 0/0 pair is an unset placeholder: current Manager 1017's JD says 5-12.
        if (type(minimum) in (int, float) and type(maximum) in (int, float)
                and 0 <= minimum <= maximum and maximum > 0):
            text += f"\nRequired experience: {minimum:g}-{maximum:g} years of experience."
        job["description"] = text
        return ""

    with ThreadPoolExecutor(max_workers=4) as pool:
        for error in pool.map(enrich, jobs.values()):
            if error:
                errors.append(error)
    if errors and not jobs:
        raise RuntimeError("; ".join(errors[:8]))
    return CollectionResult(list(jobs.values()), status="partial" if errors else "ok", error="; ".join(errors[:8]))
