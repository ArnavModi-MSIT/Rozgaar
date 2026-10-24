"""
Standalone diagnostic for fetchers/workday.py — shows the raw HTTP status
and response so we can tell "wrong tenant/site" apart from "Akamai blocked
this request" before assuming a config is broken.

Usage: python debug/debug_workday.py   (run from project root)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

import backend.config as config

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Accept-Language": "en-US",
}

for cfg in config.WORKDAY:
    tenant, wd_server, site = cfg["tenant"], cfg["wd_server"], cfg["site"]
    base = f"https://{tenant}.{wd_server}.myworkdayjobs.com"
    url = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    headers = {**HEADERS, "Referer": f"{base}/en-US/{site}"}
    payload = {"appliedFacets": {}, "limit": 5, "offset": 0, "searchText": ""}

    print(f"--- {cfg['company']} ({tenant}.{wd_server}) ---")
    print(f"POST {url}")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"status: {r.status_code}")
        print(f"content-type: {r.headers.get('content-type')}")
        print(f"body length: {len(r.content)} bytes")
        print("body preview (first 500 chars):")
        print(r.text[:500])
    except requests.RequestException as e:
        print(f"request failed: {e}")
    print()
