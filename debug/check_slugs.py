"""
Verify which ATS slugs are live before adding them to config.py.

Extends the original check_slugs.py with Workable support (GET-based, same
shape as Greenhouse/Lever/Ashby) and a separate Workday checker (POST-based
with a JSON body — a fundamentally different shape, so it can't reuse the
same generic check() function the other four platforms share).

Pre-loaded with the companies + platforms identified from cross-referencing
santifer/career-ops's company list against real India presence (see chat
history for how each was verified). Run with no arguments to check that
whole batch in one pass, or pass your own slugs to probe something else
across all four GET-based platforms.

Usage:
    python debug/check_slugs.py                          # checks the pre-loaded batch below
    python debug/check_slugs.py razorpay cred zomato      # checks custom slugs (tries all 4 platforms each)
"""

import sys

import requests

S = requests.Session()
S.headers["User-Agent"] = "slugcheck/1.0"

ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{}?details=true",
}

# slug -> platform, for companies whose ATS we already identified — checking
# only the known platform means one request per company instead of probing
# all four blind. India-presence notes are from web research, NOT verified
# by this script — this only confirms the slug is live with a real posting
# count. To confirm postings are actually India-located, add the slug to
# config.py and run debug/debug_titles.py --company <slug> afterward.
KNOWN_COMPANIES = {
    "anthropic": "greenhouse",   # confirmed India: Bengaluru office, opened Feb 2026
    "twilio": "greenhouse",
    "talkdesk2": "greenhouse",   # NOT "talkdesk" — real slug has a "2" suffix
    "liveperson": "greenhouse",
    "dialpad": "greenhouse",     # confirmed India: Bangalore office, even has intern postings
    "openai": "ashby",
    "pinecone": "ashby",
    "vercel": "greenhouse",
    "cohere": "ashby",           # flagged: cohere.com's own careers page lists no India office —
                                  # likely NOT worth adding despite showing up in some lists
    "huggingface": "workable",   # small NYC/Paris company, India presence doubtful
}


def count(kind, data):
    if kind == "lever":
        return len(data)
    return len(data.get("jobs", []))


def check(slug, only_platform=None):
    """Returns list of (kind, status) where status is either an int posting
    count, or the string 'empty' for a valid board with zero current
    openings (as opposed to a 404, which means the slug itself is wrong).
    If only_platform is given, only that one platform is probed."""
    results = []
    platforms = [only_platform] if only_platform else list(ENDPOINTS.keys())
    for kind in platforms:
        tmpl = ENDPOINTS[kind]
        try:
            r = S.get(tmpl.format(slug), timeout=15)
        except requests.RequestException:
            continue
        if r.status_code == 404:
            continue  # slug doesn't exist on this board
        if r.status_code != 200:
            results.append((kind, f"HTTP {r.status_code}"))
            continue
        try:
            n = count(kind, r.json())
        except ValueError:
            results.append((kind, "invalid JSON response"))
            continue
        results.append((kind, n if n else "empty"))
    return results


def check_salesforce_workday():
    """Workday needs a POST with a JSON body, not a simple GET — a
    completely different shape from the other four platforms, so it can't
    share check()/ENDPOINTS. tenant/site come from Salesforce's actual
    careers URL; wd_server (wd1 vs wd12) wasn't confirmed during research,
    so both are tried here — whichever responds 200 is the real one.

    Scoped directly to India via the locationCountry facet (same GUID
    fetchers/workday.py already uses elsewhere in this project:
    c4f78be1a8f14da0ab49ce1162348a5e) so the count printed is an India-only
    total, not a global one."""
    tenant, site = "salesforce", "External_Career_Site"
    INDIA_GUID = "c4f78be1a8f14da0ab49ce1162348a5e"
    for wd_server in ["wd1", "wd12"]:
        base = f"https://{tenant}.{wd_server}.myworkdayjobs.com"
        url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
        headers = {
            "User-Agent": "slugcheck/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": f"{base}/en-US/{site}",
        }
        payload = {
            "appliedFacets": {"locationCountry": [INDIA_GUID]},
            "limit": 5,
            "offset": 0,
            "searchText": "",
        }
        try:
            r = S.post(url, json=payload, headers=headers, timeout=15)
        except requests.RequestException as e:
            print(f"  {wd_server}: request failed: {e}")
            continue
        print(f"  {wd_server}: status={r.status_code}", end="")
        if r.status_code == 200:
            data = r.json()
            total = data.get("total", 0)
            print(f" — India-scoped postings: {total}")
            for j in data.get("jobPostings", [])[:3]:
                print(f"      - {j.get('title')!r} | {j.get('locationsText')!r}")
        else:
            print(f" — body: {r.text[:150]!r}")


def _print_hits(slug, hits):
    if hits:
        for kind, status in hits:
            if status == "empty":
                print(f"  OK   {slug:<15} {kind:<10} valid board, 0 open postings right now")
            elif isinstance(status, int):
                print(f"  OK   {slug:<15} {kind:<10} {status} postings")
            else:
                print(f"  ??   {slug:<15} {kind:<10} {status}")
    else:
        print(f"  --   {slug:<15} not found — slug may be wrong, double-check")


if __name__ == "__main__":
    custom_slugs = sys.argv[1:]

    if custom_slugs:
        # Same behavior as the original check_slugs.py — probe all 4
        # GET-based platforms for each slug, since we don't know which one.
        for slug in custom_slugs:
            _print_hits(slug, check(slug))
    else:
        print("Checking known companies (Greenhouse/Ashby/Workable — one request each)...\n")
        for slug, platform in KNOWN_COMPANIES.items():
            _print_hits(slug, check(slug, only_platform=platform))

        print("\nChecking Salesforce (Workday — separate check, POST-based)...")
        check_salesforce_workday()
