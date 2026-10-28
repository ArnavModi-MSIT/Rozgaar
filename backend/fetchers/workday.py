"""
Fetcher for Workday-hosted career sites (*.wdN.myworkdayjobs.com).

Endpoint: POST https://{tenant}.{wd_server}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
Body: {"appliedFacets": {}, "limit": N, "offset": N, "searchText": ""}

CAUTION: Workday deployments commonly sit behind Akamai bot management, the
same category of protection that blocked jobs.zs.com (iCIMS/Jibe) even with
browser-matched headers. If a config here returns 0 jobs, run debug_workday.py
first to see the raw response before assuming the tenant/site is wrong —
it may be bot-blocked rather than misconfigured, in which case this platform
isn't worth pursuing for that company (same call we made on ZS).

The list endpoint gives no description body. A per-job detail endpoint
does (confirmed via debug/debug_workday_detail.py):
  GET {base}/wday/cxs/{tenant}/{site}{externalPath} -> jobPostingInfo.jobDescription
Two opt-in ways a company's config.py entry can enable this:
  - fetch_details=True: fetch for every India/unknown-location posting
    (used for small companies, e.g. Fractal — ~140 postings, safe volume)
  - fetch_details_filter=<compiled regex>: fetch only for postings whose
    title matches, on top of the same India/unknown check (used for large
    companies where fetching everything would be a rate-limit risk, e.g.
    a large tenant — thousands of postings total, but only the Data/Analytics/AI subset
    matching the configured relevance pattern actually gets detail-fetched)
Neither is automatic — a company with neither key set gets no detail-fetch
at all, same as before this feature existed.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from backend.core.location import is_india_or_unknown, is_workday_location_placeholder, parse_country
from .standard import strip_html
from .result import CollectionResult

log = logging.getLogger("jobbot")
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Accept-Language": "en-US",
})


def _post(url, payload, referer):
    headers = {"Referer": referer}
    for attempt in range(RETRIES):
        try:
            r = SESSION.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429:
                # Rate limited — this is why pagination was silently
                # truncating to exactly 2 pages for every tenant regardless
                # of total size. Retry with backoff instead of giving up.
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # other 4xx (bad config, bot-blocked) — don't retry
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def _get(url, referer):
    headers = {"Referer": referer}
    for attempt in range(RETRIES):
        try:
            r = SESSION.get(url, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def fetch_job_detail(base, tenant, site, ext_path, referer):
    """Full description via the per-job CXS detail endpoint. See module
    docstring — jobPostingInfo.jobDescription is a single HTML field
    (unlike Lever, which splits content across multiple fields)."""
    info = fetch_job_info(base, tenant, site, ext_path, referer)
    html = info.get("jobDescription", "")
    if not html:
        return ""
    return strip_html(html, max_chars=None)


def fetch_job_info(base, tenant, site, ext_path, referer):
    data = _get(f"{base}/wday/cxs/{tenant}/{site}{ext_path}", referer)
    info = data.get("jobPostingInfo") if isinstance(data, dict) else None
    return info if isinstance(info, dict) else {}


def posting_location(info, fallback="", *, india_location_names=()):
    """Use Workday country/location metadata, preserving explicit India options."""
    country = info.get("country") or {}
    country = country.get("descriptor", "") if isinstance(country, dict) else country
    country = country.strip() if isinstance(country, str) else ""
    primary = info.get("location")
    primary = primary.strip() if isinstance(primary, str) else ""
    extras = [loc.strip() for loc in info.get("additionalLocations") or [] if isinstance(loc, str) and loc.strip()]
    verified_india = {name.casefold() for name in india_location_names}
    india_extras = [loc for loc in extras if parse_country(loc) == "India" or loc.casefold() in verified_india]
    # Walmart's documented country/state/city convention, retained from its
    # existing special-case location handling.
    india_extras += [loc for loc in extras if loc.startswith("IN ") or loc.startswith("(IND)")]
    if country.casefold() == "india":
        # The primary location's country is authoritative; foreign secondary
        # options must not be displayed as if they too were in India.
        locations = list(dict.fromkeys(([primary] if primary else []) + india_extras))
        location = "; ".join(locations) if locations else "India"
        return location if parse_country(location) == "India" else location + ", India"
    if india_extras:
        location = "; ".join(dict.fromkeys(india_extras))
        return location if parse_country(location) == "India" else location + ", India"
    locations = list(dict.fromkeys(([primary] if primary else []) + extras))
    location = "; ".join(locations) or fallback
    if country:
        return (location + ", " if location else "") + country
    return location


def fetch_workday(cfg, deadline=None):
    """cfg = {"company": ..., "tenant": ..., "wd_server": ..., "site": ...,
    "fetch_details": bool (optional), "fetch_details_filter": compiled
    regex (optional) — see module docstring for what each does}
    All four core values come from the company's careers URL, e.g.
      https://example.wd1.myworkdayjobs.com/Careers
        tenant=example  wd_server=wd1  site=Careers
    deadline: an optional time.monotonic() timestamp — pagination stops
    (returning whatever's been collected so far) once past it, since a
    single company's fetch can otherwise run far longer than the overall
    run's time budget (observed: 211s for 6 companies even parallelized —
    Akamai appears to rate-limit by source IP across ALL Workday tenants,
    not per-tenant, so concurrency here doesn't help the way it does on
    other platforms and backoff delays add up fast).
    """
    tenant = cfg["tenant"]
    wd_server = cfg["wd_server"]
    site = cfg["site"]
    base = f"https://{tenant}.{wd_server}.myworkdayjobs.com"
    url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    referer = f"{base}/en-US/{site}"
    # Optional server-side facet filtering (e.g. {"locationCountry":
    # ["<country GUID>"]} scopes results to one country at the API level,
    # same efficiency win as Oracle's location_id for JPMC). Empty dict =
    # unfiltered, the behavior every existing company keeps.
    applied_facets = cfg.get("applied_facets") or {}
    # Optional server-side full-text scoping, for a tenant with neither a
    # working country facet nor a location string worth filtering on
    # client-side (e.g. Walmart's general-retail Workday site — see its
    # config.py entry: unscoped pagination there would mean wading through
    # tens of thousands of US store-associate postings for a few hundred
    # real India tech roles). Empty string = unfiltered, the behavior every
    # existing company keeps.
    search_text = cfg.get("search_text", "")

    jobs, errors = [], []
    offset = 0
    limit = 20
    known_total = None  # Workday only returns an accurate `total` on the
    # FIRST page of a query — every page after that returns total=0 even
    # though jobPostings keeps coming back full. Using each page's own
    # (broken) total to decide when to stop caused every tenant to halt
    # after exactly 2 pages regardless of real size. Fix: capture total
    # once, from page one, and trust it for the rest of the pagination.
    max_offset = 10000  # emergency fallback only — the real stop condition
    # is known_total (set below) or a short page; this just prevents an
    # infinite loop in the rare case total never comes back at all.
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("listing deadline reached")
            break
        payload = {"appliedFacets": applied_facets, "limit": limit, "offset": offset, "searchText": search_text}
        data = _post(url, payload, referer)
        if not isinstance(data, dict) or not isinstance(data.get("jobPostings"), list):
            errors.append("listing unavailable at offset " + str(offset))
            break
        postings = data.get("jobPostings", [])
        total = data.get("total", 0)
        if known_total is None and total:
            known_total = total
        if not postings:
            break
        for j in postings:
            ext_path = j.get("externalPath", "")
            if (not isinstance(j.get('title'), str) or not j['title'].strip()
                    or not isinstance(ext_path, str) or not ext_path.startswith('/job/')
                    or '?' in ext_path or '#' in ext_path):
                errors.append('listing missing title or job detail path')
                continue
            bullets = j.get("bulletFields") or []
            req_id = bullets[0] if bullets else ext_path
            location = j.get("locationsText", "")
            if not location and len(bullets) > 1:
                location = bullets[1]
            if cfg["company"] == "walmart":
                if location.startswith("IN ") or j.get("title", "").startswith("(IND)"):
                    location += ", India"
                elif j.get("title", "").startswith("(USA)"):
                    location += ", United States"
            jobs.append({
                "company": cfg["company"],
                "source_id": req_id,
                "title": j.get("title", ""),
                "location": location,
                "url": f"{base}/en-US/{site}{ext_path}",
                # List endpoint gives no description body — filled in below
                # only for companies with fetch_details=True in config.py.
                "description": "",
                # Internal only, used below to build the detail-fetch URL —
                # never written to the database (save_job() only pulls the
                # specific keys it knows about).
                "_ext_path": ext_path,
            })
        offset += limit
        if len(postings) < limit:
            break  # short page — genuinely the last one
        if known_total and offset >= known_total:
            break
        if offset >= max_offset:
            break
        time.sleep(0.3)  # small gap between pages — Workday rate-limits bursts

    if known_total is not None and len(jobs) != known_total:
        errors.append(f"received {len(jobs)} of {known_total} listings")

    detail_filter = cfg.get("fetch_details_filter")
    enrich_enabled = cfg.get("fetch_details") or detail_filter
    if jobs and deadline is not None and time.monotonic() >= deadline:
        errors.append("detail deadline reached")
    if jobs and not (deadline is not None and time.monotonic() >= deadline):
        to_enrich = [
            j for j in jobs
            if is_workday_location_placeholder(j["location"]) or (
                enrich_enabled and is_india_or_unknown(j["location"])
                and (detail_filter is None or detail_filter.search(j["title"])))
        ]
        if to_enrich:
            log.info("workday %s: detail-fetching %d/%d job(s)", cfg["company"], len(to_enrich), len(jobs))
            # Low concurrency, same Akamai caution as the list fetch itself.
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {
                    pool.submit(fetch_job_info, base, tenant, site, j["_ext_path"], referer): j
                    for j in to_enrich
                }
                for f in futures:
                    job = futures[f]
                    try:
                        info = f.result()
                        # Requisition IDs, when supplied, must match the listing.
                        if info.get("jobReqId") and info["jobReqId"] != job["source_id"]:
                            errors.append("detail identity mismatch: " + str(job["source_id"]))
                            continue
                        job["location"] = posting_location(info, job["location"], india_location_names=cfg.get("india_location_names", ()))
                        if is_workday_location_placeholder(job["location"]):
                            errors.append("location unresolved: " + str(job["source_id"]))
                        if enrich_enabled and is_india_or_unknown(job["location"]) and (detail_filter is None or detail_filter.search(job["title"])):
                            job["description"] = strip_html(info.get("jobDescription") or "", max_chars=None)
                            if not job["description"]:
                                errors.append("description unavailable: " + str(job["source_id"]))
                    except Exception as e:
                        log.exception("workday detail fetch failed for %s: %s", job.get("source_id"), e)
                        errors.append("detail unavailable: " + str(job["source_id"]))

    # _ext_path was only ever needed to build the detail-fetch URL above —
    # strip it so the returned job dicts actually match the documented
    # schema (company/source_id/title/location/url/description). It never
    # reached the database either way (save_job() only pulls known keys),
    # but leaving it in the returned dicts was a leaky implementation
    # detail for anything else that might inspect a job dict later.
    for job in jobs:
        job.pop("_ext_path", None)

    # Unresolved aggregate labels cannot establish an India posting. Keep
    # partial health evidence, but do not save those placeholders as vacancies.
    unresolved = [job for job in jobs if is_workday_location_placeholder(job["location"])]
    if unresolved:
        errors.append(f"excluded {len(unresolved)} unresolved aggregate locations")
    jobs = [job for job in jobs if not is_workday_location_placeholder(job["location"])]
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]))


def collect(workday_configs, deadline=None):
    if not workday_configs:
        return []
    jobs, errors, companies = [], [], {}
    # Lower concurrency than other platforms deliberately: parallel bursts
    # across Workday tenants appear to trigger MORE Akamai rate-limiting,
    # not less (observed 211s for 6 companies at max_workers=8, worse than
    # a naive sequential estimate) — likely rate-limited by source IP across
    # all *.myworkdayjobs.com subdomains, not per-tenant.
    with ThreadPoolExecutor(max_workers=min(3, len(workday_configs))) as pool:
        futures = [(cfg, pool.submit(fetch_workday, cfg, deadline)) for cfg in workday_configs]
        for cfg, f in futures:
            try:
                result = f.result()
                jobs += result
                status, error = getattr(result, "status", "ok"), getattr(result, "error", "")
                companies[cfg["company"]] = {"status": status, "error": error}
                if status != "ok":
                    errors.append(cfg["company"] + ": " + error)
            except Exception as e:
                log.exception("a workday company fetch failed: %s", e)
                companies[cfg["company"]] = {"status": "failed", "error": str(e)[:300]}
                errors.append(cfg["company"] + ": " + str(e))
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors[:5]), companies=companies)
