"""
Fetcher for ainterviews.com-powered job boards — an AI-interview-platform
vendor that also hosts a company's public job board (multi-tenant,
confirmed via Lenskart's tenant "lenskart_ho"). Found via a real
Playwright network capture buried in ad-tech/analytics noise on
lenskart.com/careers-at-lenskart:
  GET https://ainterviews.com/api/job_board/{tenant}/jobs/
  -> {"jobs": [...], "filters": {...}}
Unauthenticated, no pagination needed (confirmed: Lenskart returns all 67
postings in one response, no page/limit params required or honored).

Full HTML description already included per job — no separate detail
fetch needed. `apply_url` is a relative path off ainterviews.com itself
(not the company's own domain) — confirmed live, resolves to a real
job detail page.

cfg = {"company": ..., "tenant": ...}. tenant is the slug in the
careers-page's own API URL — found the same way as every other
fingerprinted platform in this project: capture the real network request
a company's careers page makes, not guessed from the company name.
"""

import logging

import requests

log = logging.getLogger("jobbot")

BASE = "https://ainterviews.com"
TIMEOUT = 15
RETRIES = 3


def _get(tenant):
    url = f"{BASE}/api/job_board/{tenant}/jobs/"
    for attempt in range(RETRIES):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=TIMEOUT)
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
    tenant = cfg["tenant"]
    data = _get(tenant)
    if not data:
        return []
    jobs = []
    for j in data.get("jobs", []):
        apply_url = j.get("apply_url") or ""
        url = f"{BASE}{apply_url}" if apply_url.startswith("/") else apply_url
        jobs.append({
            "company": cfg["company"],
            "source_id": str(j.get("id", "")),
            "title": j.get("title", ""),
            "location": j.get("location", "") or "",
            "url": url,
            "description": j.get("description", "") or "",
        })
    return jobs


def collect(configs, deadline=None):
    jobs = []
    failures = 0
    for cfg in configs:
        try:
            jobs += fetch_company(cfg)
        except Exception as e:
            log.exception("ainterviews company '%s' failed: %s", cfg.get("company"), e)
            failures += 1
    if configs and failures == len(configs):
        raise RuntimeError("ainterviews fetcher: all companies failed")
    return jobs
