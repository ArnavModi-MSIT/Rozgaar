"""
Fetcher for Oracle Recruiting Cloud (ORC) — powers Amex, Oracle itself, and
many large enterprise career sites (recognizable by *.fa.<dc>.oraclecloud.com
career URLs). Returns the same job-dict shape as fetchers/standard.py.

The list endpoint's ShortDescriptionStr/ExternalDescriptionStr fields come
back empty for at least some tenants (confirmed: Amex) even though the
public careers page clearly renders a full description. The real content
comes from a separate per-requisition detail call — confirmed via
debug/debug_oracle.py against several candidate request shapes:
  - recruitingCEJobRequisitions/{id} (direct resource)        -> 404
  - recruitingCEJobRequisitions?finder=ById;Id=...,siteNumber=... -> 400
  - recruitingCEJobRequisitions?finder=ById;Id=...            -> 400
  - recruitingCEJobRequisitionDetails?finder=ById;Id=...      -> 200, real data
Only the last one — a different resource name, no siteNumber — works.

To keep the extra HTTP call bounded, detail is only fetched for postings
that are India-based or whose location couldn't be parsed at all (see
core.location.is_india_or_unknown) — this never drops a job, only skips
the extra enrichment call for it.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from core.location import is_india_or_unknown
from fetchers.standard import SESSION, TIMEOUT, _get, strip_html  # noqa: F401 (re-exported for debug scripts)

log = logging.getLogger("jobbot")


def fetch_requisition_detail(base, req_id):
    """Full description via the per-requisition detail endpoint. See module
    docstring for why this exact resource/finder combination, and not the
    more obvious-looking alternatives, is the one that actually works.

    Combines three sections — ExternalDescriptionStr, Responsibilities,
    Qualifications — confirmed via debug/debug_oracle.py to be the
    job-specific content. OrganizationDescriptionStr (benefits) and
    CorporateDescriptionStr (company culture blurb) are deliberately
    excluded: identical boilerplate repeated on every posting from the
    same company, which would only dilute TF-IDF matching rather than
    help it. Internal* fields are duplicates of External* (same lengths),
    so only External is used.

    Each section is stripped without truncation (max_chars=None) before
    joining — the combined raw HTML across all three sections runs
    ~10k+ chars for a typical posting, well past strip_html's normal
    3000-char single-posting default; truncating per-section first would
    cut Qualifications off entirely. The final joined result is capped
    once, generously, instead."""
    url = (
        f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
        f"?onlyData=true&expand=all&finder=ById;Id={req_id}"
    )
    data = _get(url)
    if not data:
        return ""
    items = data.get("items") or []
    if not items:
        return ""
    item = items[0]
    sections = [
        item.get("ExternalDescriptionStr") or "",
        item.get("ExternalResponsibilitiesStr") or "",
        item.get("ExternalQualificationsStr") or "",
    ]
    combined = "\n\n".join(strip_html(s, max_chars=None) for s in sections if s)
    return combined[:6000]


def fetch_oracle(cfg, deadline=None):
    """cfg = {"company": ..., "tenant": ..., "site": ..., "datacenter": ...
    (optional), "location_id": ... (optional)}
    Values come straight from the company's careers URL. Two host
    structures exist across different Oracle customers — confirmed via
    debug/debug_oracle_jpmc.py:
      Amex:  https://egug.fa.us2.oraclecloud.com/...  (tenant.fa.DATACENTER.oraclecloud.com)
      JPMC:  https://jpmc.fa.oraclecloud.com/...       (tenant.fa.oraclecloud.com, no datacenter)
    "datacenter" is optional in cfg — omit it for hosts like JPMC's.
    "location_id" is also optional: appending it to the finder string as
    an extra param (confirmed working, not documented anywhere — found by
    testing) scopes results server-side instead of fetching every global
    posting and filtering after. For JPMC this cut 7278 global postings
    down to 434 India-only at the API level. Companies without a known
    location_id still get the client-side
    is_india_or_unknown() filtering everywhere else already handles.
    deadline: an optional time.monotonic() timestamp — pagination stops
    once past it, returning whatever's been collected so far (same pattern
    as fetchers/workday.py / fetchers/phenom.py — companies with large
    posting counts can otherwise run well past the outer run() time budget,
    which can't interrupt a single blocking fetch call).

    "base_url" (optional): a few ORC customers (confirmed: Dell,
    enterpriseplatform.dell.com) map the whole product onto their own
    custom domain instead of the standard tenant.fa.DATACENTER.oraclecloud.com
    hostname — when set, this is used directly as the base and
    tenant/datacenter are ignored."""
    if cfg.get("base_url"):
        base = cfg["base_url"]
    else:
        datacenter = cfg.get("datacenter")
        if datacenter:
            base = f"https://{cfg['tenant']}.fa.{datacenter}.oraclecloud.com"
        else:
            base = f"https://{cfg['tenant']}.fa.oraclecloud.com"
    location_id = cfg.get("location_id")
    jobs = []
    offset = 0
    page_size = 100
    while True:
        if deadline is not None and time.monotonic() >= deadline:
            break
        finder = (
            f"findReqs;siteNumber={cfg['site']},"
            "facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3B"
            "CATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,"
            f"limit={page_size},offset={offset},sortBy=POSTING_DATES_DESC"
        )
        if location_id:
            finder += f",locationId={location_id}"
        url = (
            f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList.secondaryLocations"
            f"&finder={finder}"
        )
        data = _get(url)
        if not data:
            break
        items = data.get("items") or []
        if not items:
            break
        reqs = items[0].get("requisitionList", [])
        # TotalJobsCount defaulting to 0 used to make "offset >= total"
        # trivially true after just page one for any tenant that omits or
        # zeroes this field — same failure class as fetchers/icims.py had
        # (see its fix). "not reqs" (this page came back empty) is the
        # real, reliable stop signal; the total-based check is only
        # trusted when a real (truthy) total was actually returned.
        total = items[0].get("TotalJobsCount", 0)
        for j in reqs:
            loc = j.get("PrimaryLocation", "") or ""
            secondary = j.get("secondaryLocations") or []
            loc_all = ", ".join([loc] + [s.get("Name", "") for s in secondary if s.get("Name")])
            req_id = j.get("Id", "")
            jobs.append({
                "company": cfg["company"],
                "source_id": str(req_id),
                "title": j.get("Title", ""),
                "location": loc_all,
                "url": f"{base}/hcmUI/CandidateExperience/en/sites/{cfg['site']}/job/{req_id}",
                # List endpoint's description fields are empty for at least
                # some tenants — filled in below via detail-fetch, for
                # India/unknown-location postings only.
                "description": "",
            })
        offset += page_size
        if not reqs or (total and offset >= total):
            break

    if deadline is not None and time.monotonic() >= deadline:
        return jobs  # out of time budget — skip the enrichment pass entirely

    to_enrich = [j for j in jobs if is_india_or_unknown(j["location"])]
    if to_enrich:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch_requisition_detail, base, j["source_id"]): j for j in to_enrich}
            for f in futures:
                job = futures[f]
                try:
                    desc = f.result()
                    if desc:
                        job["description"] = desc
                except Exception as e:
                    log.exception("oracle detail fetch failed for %s: %s", job["source_id"], e)

    return jobs


def collect(oracle_configs, deadline=None):
    if not oracle_configs:
        return []
    jobs = []
    with ThreadPoolExecutor(max_workers=min(8, len(oracle_configs))) as pool:
        futures = [pool.submit(fetch_oracle, cfg, deadline) for cfg in oracle_configs]
        for f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("an oracle company fetch failed: %s", e)
    return jobs
