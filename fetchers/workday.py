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
    Genpact — ~2000 postings total, but only the Data/Analytics/AI subset
    matching GENPACT_RELEVANT in config.py actually gets detail-fetched)
Neither is automatic — a company with neither key set gets no detail-fetch
at all, same as before this feature existed.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from core.location import is_india_or_unknown
from .standard import strip_html

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
    url = f"{base}/wday/cxs/{tenant}/{site}{ext_path}"
    data = _get(url, referer)
    if not data:
        return ""
    html = (data.get("jobPostingInfo") or {}).get("jobDescription", "")
    if not html:
        return ""
    return strip_html(html, max_chars=None)[:6000]


def fetch_workday(cfg, deadline=None):
    """cfg = {"company": ..., "tenant": ..., "wd_server": ..., "site": ...,
    "fetch_details": bool (optional), "fetch_details_filter": compiled
    regex (optional) — see module docstring for what each does}
    All four core values come from the company's careers URL, e.g.
      https://accenture.wd103.myworkdayjobs.com/AccentureCareers
        tenant=accenture  wd_server=wd103  site=AccentureCareers
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

    jobs = []
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
            break
        payload = {"appliedFacets": applied_facets, "limit": limit, "offset": offset, "searchText": search_text}
        data = _post(url, payload, referer)
        if not data:
            break
        postings = data.get("jobPostings", [])
        total = data.get("total", 0)
        if known_total is None and total:
            known_total = total
        if not postings:
            break
        for j in postings:
            ext_path = j.get("externalPath", "")
            bullets = j.get("bulletFields") or []
            req_id = bullets[0] if bullets else ext_path
            # Some tenants (confirmed: Accenture) don't populate locationsText
            # at all — the location shows up as a second bulletFields entry
            # instead. Fall back to it, skipping anything that looks like
            # another req-id-shaped token rather than a place name.
            location = j.get("locationsText", "")
            if not location and len(bullets) > 1:
                location = bullets[1]
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

    detail_filter = cfg.get("fetch_details_filter")
    enrich_enabled = cfg.get("fetch_details") or detail_filter
    if enrich_enabled and jobs and not (deadline is not None and time.monotonic() >= deadline):
        to_enrich = [
            j for j in jobs
            if is_india_or_unknown(j["location"])
            and (detail_filter is None or detail_filter.search(j["title"]))
        ]
        if to_enrich:
            log.info("workday %s: detail-fetching %d/%d job(s)", cfg["company"], len(to_enrich), len(jobs))
            # Low concurrency, same Akamai caution as the list fetch itself.
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {
                    pool.submit(fetch_job_detail, base, tenant, site, j["_ext_path"], referer): j
                    for j in to_enrich
                }
                for f in futures:
                    job = futures[f]
                    try:
                        desc = f.result()
                        if desc:
                            job["description"] = desc
                    except Exception as e:
                        log.exception("workday detail fetch failed for %s: %s", job.get("source_id"), e)

    # _ext_path was only ever needed to build the detail-fetch URL above —
    # strip it so the returned job dicts actually match the documented
    # schema (company/source_id/title/location/url/description). It never
    # reached the database either way (save_job() only pulls known keys),
    # but leaving it in the returned dicts was a leaky implementation
    # detail for anything else that might inspect a job dict later.
    for job in jobs:
        job.pop("_ext_path", None)

    return jobs


def collect(workday_configs, deadline=None):
    if not workday_configs:
        return []
    jobs = []
    # Lower concurrency than other platforms deliberately: parallel bursts
    # across Workday tenants appear to trigger MORE Akamai rate-limiting,
    # not less (observed 211s for 6 companies at max_workers=8, worse than
    # a naive sequential estimate) — likely rate-limited by source IP across
    # all *.myworkdayjobs.com subdomains, not per-tenant.
    with ThreadPoolExecutor(max_workers=min(3, len(workday_configs))) as pool:
        futures = [pool.submit(fetch_workday, cfg, deadline) for cfg in workday_configs]
        for f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("a workday company fetch failed: %s", e)
    return jobs
