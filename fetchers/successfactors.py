"""Collect public SAP SuccessFactors career listings.

The default search variant parses HTML cards with startrow pagination and
optionally fetches descriptions for India-or-unknown locations.
The RMK variant posts to /services/recruiting/v1/jobs with categoryId,
pageNumber and optional facetFilters. Its list response lacks descriptions.
Configure company, host, variant, category_id, max_pages and facet_filters
as appropriate for the actual tenant. Shared parsing supports custom location
field names; these are not guaranteed to be uniform across employers.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

from core.location import is_india_or_unknown
from fetchers.http_client import get_text
from fetchers.standard import strip_html

log = logging.getLogger("jobbot")

PAGE_SIZE = 25  # confirmed from real responses — the site serves 25 rows
# per page regardless of any parameter we pass.
MAX_PAGES = 120  # Safety cap: 3,000 listings.

RMK_PAGE_SIZE = 10  # confirmed from real responses — the API always
# returns 10 records regardless of the page number requested.
RMK_MAX_PAGES = 100  # hard cap for termination safety (1,000 postings).

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
})

# Trailing numeric segment of a job href is the requisition id, e.g.
# "/PayU/job/Gurgaon-P3-Assistant-Manager-BSM/53951080/" -> "53951080".
_JOB_ID_RE = re.compile(r"/(\d+)/?$")

# SuccessFactors writes the country as an ISO 3166 alpha-2 code, not a
# name: "Gurgaon, IN", "Bengaluru, IN", sometimes a bare "IN"/"US".
#
# That form is actively DANGEROUS downstream and must be normalized here,
# not left for core/location.py to interpret: "IN" is India's ISO code
# AND Indiana's US state abbreviation, and parse_country()'s US-state
# fallback wins that collision — so "Gurgaon, IN" resolved to "United
# States", is_india_or_unknown() returned False, and run.py's save-time
# filter would have silently DROPPED every Indian posting this fetcher
# produces. Confirmed live before this fix: 231 NCR postings, only 28
# classed India-or-unknown. ("CA" -> Canada vs California is the same
# trap, one code further down this map.)
#
# Fixed HERE rather than in core/location.py deliberately: only this
# fetcher knows its trailing segment is a COUNTRY code (so "IN"/"CA" are
# unambiguous in this context), while "Indianapolis, IN" reaching
# parse_country() from anywhere else genuinely IS the US and must keep
# resolving that way. Verified no existing saved row from any other
# source uses a trailing ", IN", so nothing else is affected. Same
# "normalize at the fetcher so shared parsing reads it cleanly" pattern
# fetchers/eightfold.py already uses for its own location format.
_ISO_COUNTRY_NAMES = {
    "in": "India", "us": "United States", "gb": "United Kingdom",
    "uk": "United Kingdom", "ca": "Canada", "au": "Australia",
    "sg": "Singapore", "de": "Germany", "ie": "Ireland",
    "nl": "Netherlands", "fr": "France", "ae": "United Arab Emirates",
    "pl": "Poland", "ph": "Philippines", "mx": "Mexico", "br": "Brazil",
    "jp": "Japan", "cn": "China", "es": "Spain",
}


def _normalize_location(location):
    """Expands a trailing ISO alpha-2 country code to the full country
    name so core/location.py can parse it correctly — see
    _ISO_COUNTRY_NAMES above for why this is a correctness fix, not
    cosmetics. An unrecognized trailing segment is left untouched rather
    than guessed at."""
    if not location:
        return ""
    parts = [p.strip() for p in location.split(",") if p.strip()]
    if not parts:
        return location
    name = _ISO_COUNTRY_NAMES.get(parts[-1].lower())
    if name is None:
        return location
    return ", ".join(parts[:-1] + [name])


def _search_page(host, startrow):
    url = (
        f"https://{host}/search/?q=&sortColumn=referencedate"
        f"&sortDirection=desc&startrow={startrow}"
    )
    return get_text(SESSION, url)


# Some postings genuinely carry a placeholder instead of a real
# description — confirmed live on PayU: "M3 Director - Data Science" has
# literally "NA" where another posting on the same site has 1,250 real
# characters. That's the employer's own data, not a scrape failure, but
# storing the literal string "NA" is worse than storing nothing: it would
# be embedded by core/matcher.py, shown as the description in the UI, and
# is indistinguishable downstream from a real (if useless) description.
# "" already means "no description available" everywhere in this project.
_PLACEHOLDER_DESCRIPTIONS = {"na", "n/a", "-", "--", "tbd", "none", "."}


def fetch_job_description(host, href):
    """Full description via the job detail page's
    `data-careersite-propertyid="description"` element. Returns "" on any
    failure — a missing description is never a reason to drop the job
    itself (same rule as fetchers/oracle.py's detail fetch)."""
    html = get_text(SESSION, f"https://{host}{href}")
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one('[data-careersite-propertyid="description"]')
    if el is None:
        return ""
    text = strip_html(el.decode_contents(), max_chars=None)[:6000]
    if text.strip().lower() in _PLACEHOLDER_DESCRIPTIONS:
        return ""
    return text


def _parse_row(row, cfg):
    title_el = row.select_one("a.jobTitle-link")
    if title_el is None:
        return None
    title = title_el.get_text(strip=True)
    href = title_el.get("href", "")

    loc_el = row.select_one("span.jobLocation")
    location = _normalize_location(loc_el.get_text(" ", strip=True) if loc_el else "")

    m = _JOB_ID_RE.search(href)
    # Fall back to the href itself when no numeric id is present — an
    # empty source_id would make core/storage.py's job_id() collapse
    # every id-less posting onto one hash-of-empty key.
    source_id = m.group(1) if m else href

    return {
        "company": cfg["company"],
        "source_id": str(source_id),
        "title": title,
        "location": location,
        "url": f"https://{cfg['host']}{href}" if href.startswith("/") else href,
        # Filled in below only when fetch_details is enabled for this
        # company — the listing page carries no description body.
        "description": "",
        # Internal only, used to build the detail-fetch URL; stripped
        # before returning, same as fetchers/workday.py's _ext_path.
        "_href": href,
    }


def fetch_successfactors(cfg, deadline=None):
    """deadline: an optional time.monotonic() timestamp — pagination stops
    once past it, returning whatever's been collected so far. Same pattern
    as fetchers/oracle.py / fetchers/workday.py."""
    host = cfg["host"]
    jobs = []
    seen_ids = set()

    for page in range(MAX_PAGES):
        if deadline is not None and time.monotonic() >= deadline:
            break
        html = _search_page(host, page * PAGE_SIZE)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("tr.data-row")
        if not rows:
            break

        new_on_page = 0
        for row in rows:
            job = _parse_row(row, cfg)
            if job is None or not job["title"]:
                continue
            if job["source_id"] in seen_ids:
                continue
            seen_ids.add(job["source_id"])
            jobs.append(job)
            new_on_page += 1
        if new_on_page == 0:
            break  # endpoint re-serving old rows — done
        if len(rows) < PAGE_SIZE:
            break  # short page — genuinely the last one
        time.sleep(0.3)  # polite gap between page requests
    else:
        # for/else: only reached when the loop ran all MAX_PAGES times
        # without ever breaking — i.e. the site still had more to give and
        # the cap, not the data, is what stopped us. Logged loudly so a
        # truncated result is never mistaken for a complete one.
        log.warning(
            "successfactors %s: stopped at the MAX_PAGES cap (%d pages, %d postings) — "
            "results are TRUNCATED, this tenant has more postings than were fetched",
            cfg["company"], MAX_PAGES, len(jobs),
        )

    if cfg.get("fetch_details") and jobs and not (deadline is not None and time.monotonic() >= deadline):
        to_enrich = [j for j in jobs if is_india_or_unknown(j["location"])]
        if to_enrich:
            log.info("successfactors %s: detail-fetching %d/%d job(s)",
                     cfg["company"], len(to_enrich), len(jobs))
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {pool.submit(fetch_job_description, host, j["_href"]): j for j in to_enrich}
                for f in futures:
                    job = futures[f]
                    try:
                        desc = f.result()
                        if desc:
                            job["description"] = desc
                    except Exception as e:
                        log.exception("successfactors detail fetch failed for %s: %s",
                                      job.get("source_id"), e)

    for job in jobs:
        job.pop("_href", None)
    return jobs


def _rmk_location(record):
    """RMK's list response gives city and country as SEPARATE fields, but
    the exact field NAMES are tenant-specific custom SuccessFactors config,
    not a platform standard — confirmed two genuinely different shapes:
      Custom tenant:            custprimecity / custCountryRegion
      Standard Chartered: jobLocationShort / jobLocationCountry (and only
        present at all when the query's facetFilters includes a location
        key — confirmed live: an unfiltered/keyword-only query silently
        omits these fields entirely, they're not just empty)
    Tries both, first non-empty wins. custprimecity is also genuinely None
    on some records (e.g. certain "Technical Architect" postings)
    — falls back to country alone rather than crashing on a None.join()."""
    city = record.get("custprimecity") or ""
    countries = record.get("custCountryRegion") or []
    country = countries[0] if countries else ""
    if not city and not country:
        short = record.get("jobLocationShort") or []
        if short:
            return short[0].strip()
        countries2 = record.get("jobLocationCountry") or []
        country = countries2[0] if countries2 else ""
    return ", ".join(p for p in (city, country) if p)


def fetch_successfactors_rmk(cfg, deadline=None):
    """The "rmk" variant — see module docstring. POSTs a JSON body instead
    of scraping HTML; PAGE_SIZE/pagination semantics are otherwise the
    same shape as fetch_successfactors above (short/empty page = done).

    "facet_filters" (optional): passed straight through as the request's
    own facetFilters object. Two confirmed reasons a tenant might need
    this, both found via Standard Chartered: (1) some tenants only
    include location fields in the response AT ALL when the query's
    facetFilters contains a location-shaped key — see _rmk_location's own
    docstring; (2) it also genuinely scopes the result set server-side
    (confirmed: facetFilters={"jobLocationCountry": ["India"]} returns
    only India postings). Omit for tenants where the plain
    {} query already includes location fields and no server-side scoping
    was found to work at all."""
    host = cfg["host"]
    url = f"https://{host}/services/recruiting/v1/jobs"
    referer = f"https://{host}/"
    max_pages = min(cfg.get("max_pages", RMK_MAX_PAGES), RMK_MAX_PAGES)
    facet_filters = cfg.get("facet_filters") or {}

    jobs = []
    seen_ids = set()

    for page in range(max_pages):
        if deadline is not None and time.monotonic() >= deadline:
            break
        body = {
            "locale": "en_US", "pageNumber": page, "sortBy": "", "keywords": "",
            "location": "", "facetFilters": facet_filters, "brand": "", "skills": [],
            "categoryId": cfg["category_id"], "alertId": "", "rcmCandidateId": "",
        }
        try:
            r = SESSION.post(url, json=body, headers={"Referer": referer}, timeout=25)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("successfactors(rmk) %s: request failed on page %d: %s",
                        cfg["company"], page, e)
            break

        results = data.get("jobSearchResult") or []
        if not results:
            break

        new_on_page = 0
        for entry in results:
            rec = entry.get("response") or {}
            job_id = rec.get("id")
            if not job_id or job_id in seen_ids:
                continue
            title = rec.get("unifiedStandardTitle") or ""
            url_title = rec.get("urlTitle") or rec.get("unifiedUrlTitle") or ""
            if not title:
                continue
            seen_ids.add(job_id)
            jobs.append({
                "company": cfg["company"],
                "source_id": str(job_id),
                "title": title,
                "location": _rmk_location(rec),
                "url": f"https://{host}/job/{url_title}/{job_id}-en_US",
                # No description field exists in this variant's list
                # response and no working detail endpoint was found —
                # see module docstring.
                "description": "",
            })
            new_on_page += 1

        if new_on_page == 0:
            break  # endpoint re-serving old rows — done
        if len(results) < RMK_PAGE_SIZE:
            break  # short page — genuinely the last one
        time.sleep(0.3)
    else:
        log.warning(
            "successfactors(rmk) %s: stopped at the page cap (%d pages, %d postings) — "
            "this is a deliberate sample, not the tenant's full pool (see RMK_MAX_PAGES)",
            cfg["company"], max_pages, len(jobs),
        )

    return jobs


def collect(configs, deadline=None):
    if not configs:
        return []
    jobs = []
    failures = 0
    with ThreadPoolExecutor(max_workers=min(8, len(configs))) as pool:
        futures = {}
        for cfg in configs:
            fn = fetch_successfactors_rmk if cfg.get("variant") == "rmk" else fetch_successfactors
            futures[pool.submit(fn, cfg, deadline)] = cfg
        for f in futures:
            cfg = futures[f]
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("successfactors fetch failed for %s: %s", cfg.get("company"), e)
                failures += 1

    if failures == len(configs):
        # Every configured company errored, not just returned zero
        # postings — surface this so run.py records status="failed"
        # instead of an indistinguishable "0 jobs, ok".
        raise RuntimeError(f"successfactors fetcher: all {len(configs)} company fetch(es) failed")
    return jobs
