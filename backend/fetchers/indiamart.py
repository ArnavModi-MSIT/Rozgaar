"""
Fetcher for IndiaMART's job board, hosted on a third-party vendor
(klimb.io — a chatbot-driven recruiting widget). Found via a real
Playwright network capture on careers.indiamart.com. No standard "list
all jobs" endpoint exists — the only real jobs-returning call, found by
searching the site's own production.min.js bundle for its fetch() call,
is the chatbot's own search:
  GET https://joblist.klimb.io/ChatBot/getJobs?term={term}&location=&customer={customer_id}
customer_id ("5dd7966c6c4d197f68105048" for IndiaMART) was itself found
via a real captured request (ChatBot/getCustomerId/indiamart).

DELIBERATE WORKAROUND, not a real "list everything" call: term="" 500s,
so this searches term="e" instead — the single most common English letter,
confirmed live to surface 479 of IndiaMART's real postings (vs. e.g.
term="engineer" returning only 8). This is NOT guaranteed complete (a
title containing no "e" at all — rare, but possible, e.g. an all-acronym
title — would be missed), but it's the best available substitute for a
genuine listing endpoint this vendor doesn't expose. No pagination/limit
param was found either; this returns everything term="e" matches in one
response.

No description field exists in the search response (confirmed: only
location/title/formattedTitle/id) — same "no per-job body in the list
response" situation as fetchers/goldman_sachs.py, so no separate detail
fetch was built for this either. Job detail URL confirmed live:
https://joblist.klimb.io/job/{id}

Real volume at last check: 479 matched postings, 109 NCR (23%, Noida-
heavy — reflects IndiaMART's real HQ) — but skewed heavily toward field
sales/telesales roles ("Field Sales and Client Acquisition | Executive
B2B Sales"), not engineering. Left in, same as this project's other
mixed-relevance-but-real-volume companies — the resume relevance gate
downstream is what should filter title-level noise, not this fetcher.
"""

import logging

import requests

log = logging.getLogger("jobbot")

BASE = "https://joblist.klimb.io"
SEARCH_TERM = "e"
TIMEOUT = 15
RETRIES = 3


def _get(customer_id):
    url = f"{BASE}/ChatBot/getJobs"
    params = {"term": SEARCH_TERM, "location": "", "customer": customer_id}
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            if r.status_code < 500:
                return None
        except (requests.RequestException, ValueError):
            pass
    return None


def fetch_company(cfg):
    data = _get(cfg["customer_id"])
    if not data:
        return []
    jobs = []
    for j in data:
        job_id = j.get("id", "")
        if not job_id:
            continue
        location = (j.get("location") or {}).get("searchText", "")
        jobs.append({
            "company": cfg["company"],
            "source_id": str(job_id),
            "title": j.get("title", ""),
            "location": location,
            "url": f"{BASE}/job/{job_id}",
            "description": "",
        })
    return jobs


def collect(configs, deadline=None):
    jobs = []
    failures = 0
    for cfg in configs:
        try:
            jobs += fetch_company(cfg)
        except Exception as e:
            log.exception("indiamart company '%s' failed: %s", cfg.get("company"), e)
            failures += 1
    if configs and failures == len(configs):
        raise RuntimeError("indiamart fetcher: all companies failed")
    return jobs
