"""
Fetchers for the "standard" three ATS platforms: Greenhouse, Lever, Ashby.
All return a list of dicts with the same shape:
  {company, source_id, title, location, url, description}
"""

import html
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter

from fetchers.http_client import DEFAULT_TIMEOUT, get_json
from fetchers.result import CollectionResult
from core.location import parse_country

INDIA_SCOPED_BOARDS = {"databricks", "roku", "gleanwork", "okta", "purestorage", "gitlab", "squarepointcapital", "quberesearchandtechnologies","alphagrepsecurities", "nksecuritiesresearch", "worldquant", "imc", "optiverus", "mongodb", "datadog"}
INDIA_SCOPED_BOARDS.update({"commvault", "sigmoid", "fanaticsinc", "fanaticscommerce", "fanaticsfbg", "fanaticscollectibles"})

log = logging.getLogger("jobbot")

# Kept as a module-level constant even though _get() itself now delegates
# to fetchers.http_client (which has its own internal default) — several
# other files import TIMEOUT directly from here (fetchers/oracle.py does,
# re-exporting it for debug scripts; see its own import line). Removing
# this during the http_client migration broke that import with an
# ImportError at startup — restoring it for backward compatibility.
TIMEOUT = DEFAULT_TIMEOUT

MAX_DESCRIPTION_CHARS = 3000  # Legacy default for callers of strip_html().
# The three board adapters below explicitly retain full descriptions.

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "jobbot/1.0"
# collect() can make 16 Greenhouse/Lever/Ashby requests concurrently. Keep
# that many pooled connections instead of triggering urllib3's pool-full logs.
SESSION.mount("https://", HTTPAdapter(pool_connections=16, pool_maxsize=16))

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_BREAK_RE = re.compile(r"</(p|div|li|br|h[1-6])\s*/?>", re.I)


def strip_html(text, max_chars=MAX_DESCRIPTION_CHARS):
    """Normalize source descriptions to text while keeping paragraph breaks.
    Converts block-level closing tags to newlines first so list items and
    paragraphs don't get smashed together with no separation, then strips
    remaining tags and truncates to max_chars (pass None to skip
    truncation — needed when combining multiple sections, like
    fetchers/oracle.py does, where the 3000-char single-posting default
    would cut content off before the pieces are even joined).

    Paragraph breaks preserve section headings for qualification parsing
    and resume matching. Passing None retains the full description."""
    if not text:
        return ""
    # Greenhouse sometimes delivers HTML encoded inside its content string.
    # Decode before stripping tags, including a second encoding layer.
    for _ in range(2):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    text = _BLOCK_BREAK_RE.sub("\n", text)
    text = html.unescape(_TAG_RE.sub(" ", text))
    text = re.sub(r"[ \t]+", " ", text)      # runs of spaces/tabs -> one space
    text = re.sub(r"\n{3,}", "\n\n", text)   # 3+ blank lines -> one blank line
    text = text.strip()
    return text[:max_chars] if max_chars else text


def _get(url):
    """GET with retry-with-backoff on transient failures — see
    fetchers/http_client.py for the shared policy (429 now respects
    Retry-After instead of being treated as a permanent failure, unlike
    the previous per-file implementation here). Also imported directly by
    fetchers/oracle.py, so this fix covers that fetcher's list endpoint
    too, not just Greenhouse/Lever/Ashby."""
    return get_json(SESSION, url)


def _greenhouse_location(slug, job):
    location = (job.get("location") or {}).get("name", "")
    # Rubrik department pages group city-only jobs under explicit India offices.
    if slug == "rubrik" and not re.search(r"\bindia\b", location, re.I):
        offices = job.get("offices") or []
        if any(re.search(r"\bindia\b", office.get("name", ""), re.I) for office in offices):
            location = location.strip() + ", India" if location.strip() else "India"
    if slug == "arcesiumllc" and location and all(part.strip().lower() in {"bengaluru", "bangalore", "gurugram", "gurgaon", "hyderabad"} for part in location.split(";")):
        location += ", India"
    if slug in {"alphagrepsecurities", "worldquant", "mongodb"} and location:
        parts = re.split(r";|\s+OR\s+", location, flags=re.I)
        if all(part.strip().lower() in {"bengaluru", "bangalore", "gurugram", "gurgaon", "hyderabad", "mumbai", "chennai", "delhi", "new delhi", "pune"} for part in parts):
            location = location.strip() + ", India"
    if "india" not in location.lower() and slug in {"squarepointcapital", "quberesearchandtechnologies", "razorpaysoftwareprivatelimited"} and re.search(r"\b(bangalore|bengaluru|mumbai|gurgaon|gurugram|hyderabad|delhi|chennai|pune)\b", location, re.I):
        location += ", India"
    return location


def fetch_greenhouse(slug):
    # content=true pulls full HTML for matching and qualification parsing.
    # Keep full normalized text: qualifications often follow long intros.
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise RuntimeError(f"greenhouse board {slug}: missing jobs list")
    return [
        {
            "company": slug,
            "source_id": str(j.get("id", "")),
            "title": j["title"],
            "location": _greenhouse_location(slug, j),
            "url": j["absolute_url"],
            "description": strip_html(j.get("content", ""), max_chars=None),
        }
        for j in data.get("jobs", [])
        if slug not in INDIA_SCOPED_BOARDS or parse_country(_greenhouse_location(slug, j)) == "India"
    ]


def _portcast_india_locations(job):
    """Select supported Indian locations, including Lever's additional locations."""
    categories = job.get("categories") or {}
    locations = [categories.get("location") or ""] + (categories.get("allLocations") or [])
    india_cities = {"delhi", "new delhi", "bangalore", "bengaluru", "chennai", "hyderabad", "kolkata", "mumbai"}
    selected = []
    for location in locations:
        if not isinstance(location, str):
            continue
        location = location.strip()
        if location.lower() in india_cities:
            location += ", India"
        elif not re.search(r"\bIndia\b", location, re.I):
            continue
        if location not in selected:
            selected.append(location)
    return selected


def _lever_location(slug, job):
    if slug == "ion" and (job.get("country") or "").upper() == "IN":
        location = (job.get("categories") or {}).get("location") or "India"
        return location if re.search(r"\bindia\b",location,re.I) else location+", India"
    if slug == "portcast":
        return "; ".join(_portcast_india_locations(job))
    location = (job.get("categories") or {}).get("location", "")
    # Only normalize confirmed city labels on these India company boards.
    india_labels = {"bengaluru", "hyderabad", "bangalore, karnataka", "chennai, tamil nadu", "delhi ncr", "hyderabad, telangana", "jaipur, rajasthan", "kochi, kerala", "mumbai, maharashtra", "surat, gujarat"}
    if slug == "netomi" and location == "Gurugram":
        return "Gurugram, India"
    if slug in {"cred", "meesho"} and location.strip().lower() in india_labels:
        location += ", India"
    return location


def fetch_lever(slug):
    """Lever splits posting content across THREE separate fields, not one:
    - description/descriptionPlain: intro blurb only
    - lists: array of {text: heading, content: html} — this is where
      "What we're looking for", "What you'll be doing" etc. actually live
    - additional/additionalPlain: closing/benefits blurb
    Reading only description (the old behavior) silently dropped every
    bullet-point section — confirmed missing on a real CRED posting."""
    data = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if not isinstance(data, list):
        raise RuntimeError(f"lever board {slug}: expected postings list")
    jobs = []
    for j in data:
        if slug == "ion" and (j.get("country") or "").upper() != "IN":
            continue
        if slug == "portcast" and not _portcast_india_locations(j):
            continue
        # The requested Netomi searches explicitly cover these two locations.
        # Generic Remote has no India eligibility evidence and is excluded.
        if slug == "netomi" and (j.get("categories") or {}).get("location") not in {"Remote - India", "Gurugram"}:
            continue
        parts = [j.get("description", "") or j.get("descriptionPlain", "")]
        for lst in j.get("lists") or []:
            heading = lst.get("text", "")
            content = lst.get("content", "")
            if content:
                parts.append(f"{heading}\n{content}" if heading else content)
        additional = j.get("additional", "") or j.get("additionalPlain", "")
        if additional:
            parts.append(additional)
        combined = "\n\n".join(p for p in parts if p)
        jobs.append({
            "company": slug,
            "source_id": str(j.get("id", "")),
            "title": j["text"],
            "location": _lever_location(slug, j),
            "url": j["hostedUrl"],
            "description": strip_html(combined, max_chars=None),
        })
    return jobs


def _ashby_location(j):
    """Ashby has returned both a plain string and a {"name": ...} object for
    'location' depending on board config — normalize to a string either way."""
    loc = j.get("location")
    if isinstance(loc, dict):
        return loc.get("name", "")
    return loc or ""


def fetch_ashby(slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise RuntimeError(f"ashby board {slug}: missing jobs list")
    return [
        {
            "company": slug,
            "source_id": str(j.get("id", "")),
            "title": j["title"],
            "location": _ashby_location(j),
            "url": j["jobUrl"],
            "description": strip_html(
                j.get("descriptionPlain", "") or j.get("description", ""), max_chars=None
            ),
        }
        for j in data.get("jobs", [])
        if slug != "confluent" or parse_country(_ashby_location(j)) == "India"
    ]


def collect(greenhouse_slugs, lever_slugs, ashby_slugs, deadline=None):
    # One company's slow/failing API shouldn't hold up the other 10+ —
    # fetch every company concurrently and merge results. Capped so this
    # doesn't spin up dozens of threads if the company lists grow large.
    tasks = (
        [(f"greenhouse:{s}", lambda s=s: fetch_greenhouse(s)) for s in greenhouse_slugs]
        + [(f"lever:{s}", lambda s=s: fetch_lever(s)) for s in lever_slugs]
        + [(f"ashby:{s}", lambda s=s: fetch_ashby(s)) for s in ashby_slugs]
    )
    if not tasks:
        return []
    jobs = []
    failures = 0
    failed_boards = []
    def fetch_before_deadline(fn):
        if deadline is not None and time.monotonic() >= deadline:
            raise RuntimeError("shared collection deadline reached before board fetch")
        return fn()
    with ThreadPoolExecutor(max_workers=min(16, len(tasks))) as pool:
        futures = [(name, pool.submit(fetch_before_deadline, fn)) for name, fn in tasks]
        for name, f in futures:
            try:
                jobs += f.result()
            except Exception as e:
                # A bug in one company's fetcher shouldn't take down the rest.
                log.exception("a company fetch failed: %s", e)
                failures += 1
                failed_boards.append(name)
    if failures == len(tasks):
        # EVERY company errored, not just returned zero postings — without
        # this, run.py would see an empty list and record status="ok,
        # 0 jobs", indistinguishable from a genuinely quiet day across all
        # configured companies. Raising here lets it reach run.py's own
        # exception handling, which correctly records status="failed".
        raise RuntimeError(f"standard fetcher: all {len(tasks)} company fetch(es) failed")
    return CollectionResult(
        jobs,
        status="partial" if failures else "ok",
        error=f"{failures}/{len(tasks)} boards failed: {', '.join(failed_boards)}" if failures else "",
    )
