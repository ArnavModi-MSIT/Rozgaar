"""
Fetcher for Phenom People-powered career sites (recognizable by
cdn.phenompeople.com assets or a POST /widgets endpoint). Powers Mastercard,
GE Aerospace, DHL, Thermo Fisher, and many other large enterprise boards.

Each Phenom site needs a domain + refNum. On single-tenant domains (one
company per domain, e.g. careers.mastercard.com) refNum can usually be left
blank since the domain itself scopes the tenant. Multi-brand deployments
need the exact refNum pulled from the page's inline JSON — discover_refnum()
does this automatically when cfg doesn't hardcode one, so a multi-brand
config left blank now self-corrects instead of silently querying with
refNum="" (which was previously possible to trip if you forgot to set
"refnum" in config.py: this function existed but nothing ever called it).
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from .standard import strip_html  # reuse the same HTML->text helper

log = logging.getLogger("jobbot")
TIMEOUT = 15
RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "jobbot/1.0"

_REFNUM_RE = re.compile(r'"refNum"\s*:\s*"([^"]+)"')


def discover_refnum(domain):
    """Best-effort refNum discovery from the search-results page. Returns ''
    (empty refNum, valid for single-tenant domains) if none is found."""
    try:
        r = SESSION.get(f"https://{domain}/global/en/search-results", timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException:
        return ""
    m = _REFNUM_RE.search(r.text)
    return m.group(1) if m else ""


def _fetch_page(domain, refnum, offset, size):
    url = f"https://{domain}/widgets"
    payload = {
        "lang": "en_global",
        "deviceType": "desktop",
        "country": "global",
        "pageName": "search-results",
        "size": size,
        "from": offset,
        "jobs": True,
        "counts": True,
        "all_fields": ["category", "country", "city", "type"],
        "clearAll": False,
        "jdsource": "facets",
        "isSliderEnable": False,
        "pageId": "page20",
        "siteType": "external",
        "keywords": "",
        "global": True,
        "selected_fields": {},
        "sort": {"order": "desc", "field": "postedDate"},
        "locationData": {},
        "refNum": refnum,
        "ddoKey": "refineSearch",
    }
    for attempt in range(RETRIES):
        try:
            r = SESSION.post(url, json=payload, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None  # 4xx — don't retry
        except (requests.RequestException, ValueError):
            pass
        if attempt < RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])
    return None


def fetch_phenom(cfg, deadline=None):
    """cfg = {"company": ..., "domain": ..., "refnum": ..., "locale": ...}
    domain comes from the careers URL host, e.g. "careers.mastercard.com".
    refnum: if cfg omits it (or sets it to ""), discover_refnum() is used
    to pull the real value from the domain's search-results page — this
    resolves to "" anyway for single-tenant sites (a no-op there), but
    actually finds the tenant-specific refNum multi-brand deployments need
    instead of silently querying with refNum="" the whole run. Set
    "refnum" explicitly in config.py to skip this lookup (e.g. if
    discovery is ever unreliable for a given domain).
    locale: the path prefix the site actually uses, e.g. "us/en" — this
    varies per company (confirmed: Mastercard and Adobe both use "us/en",
    not the "global/en" this fetcher originally guessed, which caused links
    to resolve to the generic search page instead of the specific posting).
    Defaults to "global/en" if not given; only used as a fallback when the
    API response doesn't include its own URL.
    deadline: an optional time.monotonic() timestamp — pagination stops
    once past it, returning whatever's been collected so far. Large global
    companies (Mastercard 1162+ postings, Adobe 774+) can otherwise run
    50+ seconds per company, which the outer run() time budget in bot.py
    can't interrupt mid-call."""
    domain = cfg["domain"]
    refnum = cfg.get("refnum") or discover_refnum(domain)
    locale = cfg.get("locale", "global/en")
    jobs = []
    offset = 0
    page_size = 20
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break
        data = _fetch_page(domain, refnum, offset, page_size)
        if not data:
            break
        result = data.get("refineSearch", {})
        page_jobs = result.get("data", {}).get("jobs", [])
        total = result.get("totalHits", 0)
        if not page_jobs:
            break
        for j in page_jobs:
            job_seq = j.get("jobSeqNo") or j.get("jobId", "")
            title = j.get("title", "")
            loc = j.get("location", "") or ""
            title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            # Prefer the job DETAILS page (title/description/requirements),
            # not the apply-now form — applyUrl from the API jumps straight
            # into application, skipping the page where you'd actually read
            # what the role needs. Only fall back to applyUrl if we can't
            # build a details link (missing job_seq).
            url = (
                f"https://{domain}/{locale}/job/{job_seq}/{title_slug}"
                if job_seq else j.get("applyUrl", "")
            )
            jobs.append({
                "company": cfg["company"],
                "source_id": str(j.get("jobId", job_seq)),
                "title": title,
                "location": loc,
                "url": url,
                "description": strip_html(j.get("descriptionTeaser", "")),
            })
        offset += page_size
        if offset >= total or len(page_jobs) < page_size:
            break
    return jobs


def collect(phenom_configs, deadline=None):
    if not phenom_configs:
        return []
    jobs = []
    with ThreadPoolExecutor(max_workers=min(8, len(phenom_configs))) as pool:
        futures = [pool.submit(fetch_phenom, cfg, deadline) for cfg in phenom_configs]
        for f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("a phenom company fetch failed: %s", e)
    return jobs
