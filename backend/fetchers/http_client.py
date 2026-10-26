"""
Shared HTTP retry/backoff logic for fetchers — centralizes the retry
policy that was previously copy-pasted, with inconsistent 429 handling,
across ~10 separate fetcher modules. Only fetchers/workday.py had correct
429/Retry-After handling before this; everywhere else a transient rate
limit got treated identically to "this company doesn't exist" (a
non-retryable 4xx) — meaning a temporary rate limit could silently turn
into "platform returned 0 jobs, status=ok" in run_stats, indistinguishable
from a genuinely empty result.

Retry policy:
  429           -> respect Retry-After header if present, else backoff; RETRY
  5xx           -> backoff; RETRY
  timeout/conn  -> backoff; RETRY
  other 4xx     -> don't retry, return None immediately (bad slug, wrong
                    config, disabled endpoint — retrying won't fix it)

Both a JSON and a TEXT (HTML) variant share one implementation (_request)
— the HTML-scraping fetchers (google_careers, expedia, linkedin) each
still carry their own copy-pasted retry loop, which is exactly the
duplication this module was created to end; request_text() exists so any
new HTML fetcher gets the same correct 429/Retry-After handling instead
of becoming a fifth divergent copy.
"""

import logging
import time
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

log = logging.getLogger("jobbot")

DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = (1, 2, 4)
MAX_RETRY_AFTER_WAIT = 30  # cap in case a server sends an absurd Retry-After value


def retry_after_delay(value, fallback):
    """Parse Retry-After seconds or an HTTP date; callers choose a wait bound."""
    if value is None:
        return fallback
    try:
        seconds = float(value)
        return max(0, seconds) if math.isfinite(seconds) else fallback
    except (TypeError, ValueError):
        try:
            target = parsedate_to_datetime(value)
            if target.tzinfo is None:
                target = target.replace(tzinfo=timezone.utc)
            return max(0, (target-datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return fallback


def _request(session, method, url, parse, retries=DEFAULT_RETRIES, backoff=DEFAULT_BACKOFF,
             timeout=DEFAULT_TIMEOUT, **kwargs):
    """Shared GET/POST-with-retry core. `parse` turns a successful
    Response into the caller's return value (r.json() or r.text) — the
    ONLY difference between the JSON and text variants, so the retry
    policy itself stays defined in exactly one place."""
    last_err = None
    for attempt in range(retries):
        try:
            r = session.request(method, url, timeout=timeout, **kwargs)
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else backoff[min(attempt, len(backoff) - 1)]
                time.sleep(min(wait, MAX_RETRY_AFTER_WAIT))
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} server error")
            r.raise_for_status()
            return parse(r)
        except requests.HTTPError as e:
            if r.status_code < 500:
                return None  # other 4xx — don't retry
            last_err = e
        except (requests.RequestException, ValueError) as e:
            # ValueError covers a malformed JSON body for the json variant;
            # harmless (never raised) for the text one.
            last_err = e
        if attempt < retries - 1:
            time.sleep(backoff[min(attempt, len(backoff) - 1)])
    log.warning("request failed after %d attempts %s %s: %s", retries, method, url, last_err)
    return None


def request_json(session, method, url, **kwargs):
    """Shared GET/POST-with-retry. Returns parsed JSON, or None if every
    attempt failed or the response was a non-retryable 4xx. `method` is
    "GET" or "POST". kwargs pass straight through to session.request
    (params, json, headers, etc.) — same call shape as requests itself,
    so migrating an existing fetcher's _get()/_post() is a small,
    mechanical swap, not a rewrite."""
    return _request(session, method, url, lambda r: r.json(), **kwargs)


def request_text(session, method, url, **kwargs):
    """Same retry policy as request_json, but returns the raw response
    body as text — for HTML endpoints that get parsed with BeautifulSoup
    downstream (see fetchers/successfactors.py) rather than being JSON."""
    return _request(session, method, url, lambda r: r.text, **kwargs)


def get_json(session, url, **kwargs):
    return request_json(session, "GET", url, **kwargs)


def post_json(session, url, **kwargs):
    return request_json(session, "POST", url, **kwargs)


def get_text(session, url, **kwargs):
    return request_text(session, "GET", url, **kwargs)
