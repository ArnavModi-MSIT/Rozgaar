"""Public employer boards verified for the October 15 expansion.

These adapters read vacancy data only. They never call applicant endpoints.
Every adapter returns India postings and reports interrupted collections.
"""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .http_client import get_json, get_text, post_json
from .result import CollectionResult
from .standard import strip_html
from .peoplestrong import fetch as fetch_peoplestrong
from .c5i import fetch as fetch_c5i
from .gem import fetch as fetch_gem


def _expired(deadline):
    return deadline is not None and time.monotonic() >= deadline


def _result(jobs, errors):
    if errors and not jobs:
        raise RuntimeError("; ".join(errors[:8]))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:8]))


def _session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/html"})
    return session


def _india_locations(locations, code_key="countryCode", country_key="countryName"):
    result = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        if str(loc.get(code_key, "")).upper() != "IN" and str(loc.get(country_key, "")).lower() != "india":
            continue
        location = loc.get("location") or ", ".join(str(loc[k]) for k in ("city", "state", country_key) if loc.get(k))
        if not re.search(r"\bIndia\b", location, re.I):
            location = (location + ", India").lstrip(", ")
        if location not in result:
            result.append(location)
    return "; ".join(result)


def fetch_darwinbox(cfg, deadline=None):
    base = "https://" + cfg["host"]
    careers = base + "/ms/candidatev2/main/careers"
    jobs, seen, errors, total = [], set(), [], None
    with _session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*", "Referer": careers + "/allJobs"})
        for page in range(1, 501):
            if _expired(deadline):
                errors.append("listing deadline reached"); break
            data = post_json(session, base + "/ms/candidateapi/job/alljobs", json={"page": page, "limit": 20})
            if not isinstance(data, dict) or data.get("status") != "success" or not isinstance(data.get("data"), list):
                errors.append("Darwinbox listing unavailable"); break
            count = data.get("job_counts")
            if not isinstance(count, int) or count < 0:
                errors.append("listing total unavailable"); break
            if total is not None and total != count:
                errors.append("listing total changed")
            total = count
            added = 0
            for row in data["data"]:
                sid = str(row.get("id") or "")
                if not sid:
                    errors.append("listing ID missing"); continue
                if sid in seen:
                    continue
                seen.add(sid); added += 1
                if str(row.get("country", "")).strip().lower() != "india":
                    continue
                title = row.get("title") or row.get("designation_display_name")
                if not title:
                    errors.append("title missing: " + sid); continue
                text = strip_html(row.get("jd", ""), max_chars=None)
                # Explicit source experience belongs beside the uncut JD.
                if row.get("experience"):
                    text += "\nExperience: " + str(row["experience"])
                if not row.get("jd"):
                    errors.append("description unavailable: " + sid)
                location = re.sub(r"\s+", " ", row.get("locations") or "India")
                jobs.append(dict(company=cfg["company"], source_id=sid, title=title, location=location,
                                 description=text.strip(), url=careers + "/jobDetails/" + sid))
            if len(seen) >= total:
                break
            if not added:
                errors.append("empty or repeated listing page"); break
        else:
            errors.append("page limit reached")
    if total is None or len(seen) != total:
        errors.append(f"received {len(seen)} of {total} listings")
    return _result(jobs, errors)


def fetch_upstox(cfg, deadline=None):
    """Use official published IDs and join their full public Darwinbox JDs."""
    if _expired(deadline):
        raise RuntimeError("Upstox listing deadline reached")
    with _session() as session:
        data = get_json(session, "https://service.upstox.com/content/open/v1/jobs/")
    if not isinstance(data, dict) or data.get("success") is not True or not isinstance(data.get("data"), list):
        raise RuntimeError("Upstox official listing unavailable")
    published, errors = {}, []
    for row in data["data"]:
        if not isinstance(row, dict):
            errors.append("malformed official listing")
            continue
        if row.get("post_on_careers_page") != 1:
            continue
        if str(row.get("location_country", "")).strip().casefold() != "india":
            continue
        sid, title = row.get("job_id"), row.get("job_title")
        if not isinstance(sid, str) or not title:
            errors.append("official listing ID or title missing")
            continue
        if sid in published:
            errors.append("duplicate official ID: " + sid)
        published[sid] = row
    if not published:
        return _result([], errors)
    details = fetch_darwinbox(dict(company=cfg["company"], host="upstox.darwinbox.in"), deadline)
    if details.status != "ok":
        errors.append("Darwinbox: " + details.error)
    by_id = {job["source_id"]: job for job in details}
    jobs = []
    for sid, row in published.items():
        title = row["job_title"].strip()
        job = by_id.get(sid)
        if job is None or job["title"].strip() != title:
            errors.append("public detail missing or identity mismatch: " + sid)
            jobs.append(dict(company=cfg["company"], source_id=sid, title=title,
                             location="; ".join(loc for loc in row.get("location", [])
                                                if isinstance(loc, str) and re.search(r"\bIndia\b", loc, re.I)) or "India",
                             url="https://upstox.darwinbox.in/ms/candidatev2/main/careers/jobDetails/" + sid,
                             description=""))
            continue
        # Preserve explicit source years even when the frontend shows only a teaser.
        minimum, maximum = str(row.get("experience_from", "")), str(row.get("experience_to", ""))
        if (re.fullmatch(r"\d+(?:\.\d+)?", minimum)
                and re.fullmatch(r"\d+(?:\.\d+)?", maximum)
                and 0 <= float(minimum) <= float(maximum) and float(maximum) > 0):
            job["description"] += f"\nRequired experience: {minimum}-{maximum} years of experience."
        # Some JDs put a bare numeric requirement on an 'Experience:' header.
        # Restate that exact source span for the existing experience parser.
        match = re.search(r"(?:^|\n)\s*Experience\s*:\s*(\d+(?:\.\d+)?\s*\+?(?:\s*[-–—]\s*\d+(?:\.\d+)?)?\s*(?:years?|yrs?))\b",
                          job["description"], re.I)
        if match:
            job["description"] += "\nRequired experience: " + match[1] + " of experience."
        if row.get("employee_type"):
            job["description"] += "\nEmployment type: " + row["employee_type"]
        jobs.append(job)
    return _result(jobs, errors)


def fetch_keka(cfg, deadline=None):
    if _expired(deadline):
        raise RuntimeError("deadline reached")
    base = "https://" + cfg["host"] + "/careers"
    with _session() as session:
        rows = get_json(session, base + "/api/jobs/default/active")
    if not isinstance(rows, list):
        raise RuntimeError("Keka active jobs response unavailable")
    jobs, errors, seen = [], [], set()
    for row in rows:
        location = _india_locations(row.get("jobLocations") or [])
        if not location:
            continue
        sid, title = str(row.get("id") or ""), row.get("title")
        if not sid or not title:
            errors.append("malformed listing"); continue
        if sid in seen:
            continue
        seen.add(sid)
        text = strip_html(row.get("description", ""), max_chars=None)
        if not text:
            errors.append("description unavailable: " + sid)
        if row.get("experience"):
            text += "\nExperience: " + str(row["experience"])
        jobs.append(dict(company=cfg["company"], source_id=sid, title=title, location=location,
                         description=text.strip(), url=base + "/jobdetails/" + sid))
    return _result(jobs, errors)


def _jsonld_job(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(tag.string or tag.get_text())
        except ValueError:
            continue
        nodes = value if isinstance(value, list) else [value]
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                return node
            if isinstance(node, dict):
                nodes.extend(node.get("@graph") or [])
    # Trakstar currently emits invalid literal newlines inside JSON strings.
    # Its normal detail body is still complete readable HTML.
    body = soup.select_one(".jobdesciption")
    title = soup.select_one(".js-job-title")
    if body is not None and title is not None:
        return {"description": body.decode_contents(), "title": title.get_text(" ", strip=True)}
    return None


def fetch_trakstar(cfg, deadline=None):
    base = "https://" + cfg["host"]
    jobs, seen, errors, total, listed = [], set(), [], None, []
    with _session() as session:
        for page in range(1, 501):
            if _expired(deadline):
                errors.append("listing deadline reached"); break
            html = get_text(session, base + f"/?limit=50&p={page}")
            if not html:
                errors.append("Trakstar listing unavailable"); break
            soup = BeautifulSoup(html, "html.parser")
            match = re.search(r"View\s+(\d+)\s+Openings", soup.get_text(" ", strip=True), re.I)
            if not match:
                errors.append("listing total unavailable"); break
            if total is None:
                total = int(match[1])
            added = 0
            for card in soup.select('a[href^="/jobs/"]'):
                title = card.select_one(".js-job-list-opening-name")
                if title is None:
                    continue
                path = card["href"]
                if path in seen:
                    continue
                seen.add(path); added += 1
                node = card.select_one(".js-job-list-opening-loc")
                location = node.get("title", "").strip() if node else ""
                # These tenants publish city-only India labels too.
                if location.lower() in {"bengaluru", "bangalore", "mumbai", "gurugram", "noida"}:
                    location += ", India"
                if not re.search(r"\bIndia\b", location, re.I):
                    continue
                listed.append(dict(company=cfg["company"], source_id=path.strip("/").split("/")[-1],
                                   title=title.get_text(" ", strip=True), location=location,
                                   url=urljoin(base, path), description=""))
            if len(seen) >= total:
                break
            if not added:
                errors.append("empty or repeated listing page"); break
        else:
            errors.append("page limit reached")
        def enrich(job):
            if _expired(deadline):
                return None
            with _session() as detail_session:
                html = get_text(detail_session, job["url"])
            return _jsonld_job(html) if html else None
        with ThreadPoolExecutor(max_workers=4) as pool:
            for job, detail in zip(listed, pool.map(enrich, listed)):
                if detail and detail.get("title", "").strip() != job["title"].strip():
                    errors.append("detail identity mismatch: " + job["source_id"])
                    detail = None
                if detail and isinstance(detail.get("description"), str):
                    job["description"] = strip_html(detail["description"], max_chars=None)
                if not job["description"]:
                    errors.append("description unavailable: " + job["source_id"])
                jobs.append(job)
    if total is None or len(seen) != total:
        errors.append(f"received {len(seen)} of {total} listings")
    return _result(jobs, errors)


def _kula_stream(html):
    """Decode JSON data from React's delivered stream without executing JS."""
    chunks = []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script"):
        match = re.fullmatch(r"self\.__next_f\.push\((.*)\);?", tag.string or "", re.S)
        if match:
            value = json.loads(match[1])
            if len(value) > 1 and isinstance(value[1], str):
                chunks.append(value[1])
    return "".join(chunks)


def _kula_description(value, stream):
    if not isinstance(value, str):
        return ""
    if not re.fullmatch(r"\$[0-9a-f]+", value):
        return value
    # Flight text lengths are UTF-8 byte counts, not Python character counts.
    raw = stream.encode("utf-8")
    pos = 0
    while pos < len(raw):
        if raw[pos:pos + 1] == b"\n":
            pos += 1
            continue
        colon = raw.find(b":", pos)
        if colon < 0 or not re.fullmatch(rb"[0-9a-f]*", raw[pos:colon]):
            return ""
        reference = raw[pos:colon]
        if raw[colon + 1:colon + 2] == b"T":
            comma = raw.find(b",", colon + 2)
            size = int(raw[colon + 2:comma], 16)
            end = comma + 1 + size
            if end > len(raw):
                return ""
            if reference == value[1:].encode():
                return raw[comma + 1:end].decode("utf-8")
            pos = end
        else:
            newline = raw.find(b"\n", colon)
            pos = newline + 1 if newline >= 0 else len(raw)
    return ""


def fetch_kula(cfg, deadline=None):
    if _expired(deadline):
        raise RuntimeError("deadline reached")
    base = "https://careers.kula.ai/" + cfg["account"]
    with _session() as session:
        html = get_text(session, base)
    if not html:
        raise RuntimeError("Kula careers page unavailable")
    stream = _kula_stream(html)
    if '"accountName":' + json.dumps(cfg["account"]) not in stream:
        raise RuntimeError("Kula account identity unavailable")
    match = re.search(r'"jobs"\s*:\s*(\[)', stream)
    if not match:
        raise RuntimeError("Kula delivered jobs array unavailable")
    rows, _ = json.JSONDecoder().raw_decode(stream[match.start(1):])
    jobs, seen, errors = [], set(), []
    for row in rows:
        if not row.get("listed") or row.get("is_confidential"):
            continue
        info = row.get("ats_job") or {}
        location = _india_locations(info.get("offices") or [], "country_code", "country")
        if not location:
            continue
        sid, title = str(row.get("id") or ""), row.get("title")
        if not sid or not title:
            errors.append("malformed listing"); continue
        if sid in seen:
            continue
        seen.add(sid)
        try:
            text = strip_html(_kula_description(info.get("job_description"), stream), max_chars=None)
        except UnicodeError:
            text = ""
        if not text:
            errors.append("description unavailable: " + sid)
        jobs.append(dict(company=cfg["company"], source_id=sid, title=title, location=location,
                         description=text, url=base + "/" + sid))
    return _result(jobs, errors)


def fetch_oracle_india(cfg, deadline=None):
    base = cfg["base_url"]
    root = base + "/hcmRestApi/resources/latest/"
    jobs, seen, errors, total = [], set(), [], None
    with _session() as session:
        for offset in range(0, 50000, 100):
            if _expired(deadline):
                errors.append("listing deadline reached"); break
            finder = f"findReqs;siteNumber={cfg['site']},limit=100,offset={offset},sortBy=POSTING_DATES_DESC"
            data = get_json(session, root + "recruitingCEJobRequisitions", params={
                "onlyData": "true", "expand": "requisitionList.secondaryLocations", "finder": finder})
            items = data.get("items") if isinstance(data, dict) else None
            if not items or not isinstance(items[0].get("requisitionList"), list):
                errors.append("Oracle listing unavailable"); break
            if total is None:
                total = items[0].get("TotalJobsCount")
            added = 0
            for row in items[0]["requisitionList"]:
                sid = str(row.get("Id") or "")
                if not sid:
                    errors.append("listing ID missing"); continue
                if sid in seen:
                    continue
                seen.add(sid); added += 1
                india = []
                if row.get("PrimaryLocationCountry") == "IN":
                    india.append(row.get("PrimaryLocation") or "India")
                for loc in row.get("secondaryLocations") or []:
                    if re.search(r"\bIndia\b", loc.get("Name", ""), re.I):
                        india.append(loc["Name"])
                if not india:
                    continue
                if not row.get("Title"):
                    errors.append("title missing: " + sid); continue
                jobs.append(dict(company=cfg["company"], source_id=sid, title=row["Title"],
                                 location="; ".join(india), description="",
                                 url=f"{base}/hcmUI/CandidateExperience/en/sites/{cfg['site']}/job/{sid}"))
            if isinstance(total, int) and len(seen) >= total:
                break
            if not added:
                errors.append("empty or repeated listing page"); break
        else:
            errors.append("page limit reached")
    if not isinstance(total, int) or len(seen) != total:
        errors.append(f"received {len(seen)} of {total} listings")
    def description(job):
        if _expired(deadline):
            return ""
        with _session() as session:
            data = get_json(session, root + "recruitingCEJobRequisitionDetails", params={
                "onlyData": "true", "expand": "all", "finder": "ById;Id=" + job["source_id"]})
        items = data.get("items") if isinstance(data, dict) else None
        if not items:
            return ""
        return "\n\n".join(strip_html(items[0].get(key, ""), max_chars=None) for key in
                           ("ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr") if items[0].get(key))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, text in zip(jobs, pool.map(description, jobs)):
            job["description"] = text
            if not text:
                errors.append("description unavailable: " + job["source_id"])
    return _result(jobs, errors)


def fetch_successfactors(cfg, deadline=None):
    from .successfactors import _parse_row
    base = "https://" + cfg["host"]
    jobs, seen, errors, total = [], set(), [], None
    with _session() as session:
        for offset in range(0, 12500, 25):
            if _expired(deadline):
                errors.append("listing deadline reached"); break
            html = get_text(session, base + "/search/", params={"q": "", "locationsearch": "India", "startrow": offset})
            if not html:
                errors.append("SuccessFactors listing unavailable"); break
            soup = BeautifulSoup(html, "html.parser")
            count = re.search(r"Results\s+\d+\s*[–-]\s*\d+\s+of\s+([\d,]+)", soup.get_text(" ", strip=True))
            if total is None and count:
                total = int(count[1].replace(",", ""))
            rows, added = soup.select("tr.data-row"), 0
            for row in rows:
                job = _parse_row(row, cfg)
                if not job or not job["source_id"] or not job["title"]:
                    errors.append("malformed listing"); continue
                if job["source_id"] in seen:
                    continue
                seen.add(job["source_id"]); added += 1
                # ExxonMobil includes the Indian PIN after the ISO country.
                # Do not confuse a US state IN followed by a five-digit ZIP.
                job["location"] = re.sub(r",\s*IN(?=,\s*\d{6}\s*$)", ", India", job["location"], flags=re.I)
                if re.search(r"\bIndia\b", job["location"], re.I):
                    jobs.append(job)
            if isinstance(total, int) and len(seen) >= total:
                break
            if not added:
                # A recognized empty search is distinct from an HTML challenge.
                if not seen and re.search(r"There are currently no open positions|No jobs found", soup.get_text(" ", strip=True), re.I):
                    total = 0
                else:
                    errors.append("empty or repeated listing page")
                break
        else:
            errors.append("page limit reached")
    if total is None or len(seen) != total:
        errors.append(f"received {len(seen)} of {total} listings")
    def description(job):
        if _expired(deadline):
            return ""
        with _session() as session:
            html = get_text(session, job["url"])
        node = BeautifulSoup(html, "html.parser").select_one('[data-careersite-propertyid="description"]') if html else None
        return strip_html(node.decode_contents(), max_chars=None) if node else ""
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, text in zip(jobs, pool.map(description, jobs)):
            job.pop("_href", None)
            job["description"] = text
            if not text:
                errors.append("description unavailable: " + job["source_id"])
    return _result(jobs, errors)


def fetch_pcsx(cfg, deadline=None):
    base = "https://" + cfg["host"]
    jobs, seen, errors, total = [], set(), [], None
    with _session() as session:
        for offset in range(0, 10000, 10):
            if _expired(deadline):
                errors.append("listing deadline reached"); break
            data = get_json(session, base + "/api/pcsx/search", params={
                "domain": cfg["domain"], "location": "India", "start": offset, "query": ""})
            data = data.get("data") if isinstance(data, dict) else None
            if not isinstance(data, dict) or not isinstance(data.get("positions"), list):
                errors.append("PCSX listing unavailable"); break
            if total is None:
                total = data.get("count")
            added = 0
            for row in data["positions"]:
                sid = str(row.get("id") or "")
                if not sid:
                    errors.append("listing ID missing"); continue
                if sid in seen:
                    continue
                seen.add(sid); added += 1
                locations = [loc for loc in row.get("standardizedLocations") or [] if re.search(r",\s*IN$", loc)]
                if not locations:
                    continue
                location = "; ".join(re.sub(r",\s*IN$", ", India", loc) for loc in locations)
                if not row.get("name"):
                    errors.append("title missing: " + sid); continue
                jobs.append(dict(company=cfg["company"], source_id=sid, title=row["name"], location=location,
                                 url=base + "/careers/job/" + sid, description=""))
            if isinstance(total, int) and len(seen) >= total:
                break
            if not added:
                errors.append("empty or repeated listing page"); break
        else:
            errors.append("page limit reached")
    if total is None or len(seen) != total:
        errors.append(f"received {len(seen)} of {total} listings")
    def detail(job):
        if _expired(deadline):
            return None
        with _session() as session:
            html = get_text(session, job["url"])
        return _jsonld_job(html) if html else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, posting in zip(jobs, pool.map(detail, jobs)):
            if posting and posting.get("title", "").strip() == job["title"].strip():
                job["description"] = strip_html(posting.get("description", ""), max_chars=None)
            if not job["description"]:
                errors.append("description unavailable: " + job["source_id"])
    return _result(jobs, errors)


ADAPTERS = {"darwinbox": fetch_darwinbox, "keka": fetch_keka,
            "trakstar": fetch_trakstar, "kula": fetch_kula, "oracle": fetch_oracle_india,
            "successfactors": fetch_successfactors, "pcsx": fetch_pcsx,
            "peoplestrong": fetch_peoplestrong, "c5i": fetch_c5i, "gem": fetch_gem,
            "upstox": fetch_upstox}


def collect(configs, deadline=None):
    jobs, errors = [], []
    companies = {}
    with ThreadPoolExecutor(max_workers=min(4, len(configs) or 1)) as pool:
        futures = [(cfg, pool.submit(ADAPTERS[cfg["kind"]], cfg, deadline)) for cfg in configs]
        for cfg, future in futures:
            try:
                result = future.result()
                jobs.extend(result)
                companies[cfg["company"]] = {"status": result.status, "error": result.error}
                if result.status != "ok":
                    errors.append(cfg["company"] + ": " + result.error)
            except Exception as exc:
                errors.append(cfg["company"] + ": " + str(exc))
                companies[cfg["company"]] = {"status": "failed", "error": str(exc)[:300]}
    result = _result(jobs, errors)
    result.companies = companies
    return result
