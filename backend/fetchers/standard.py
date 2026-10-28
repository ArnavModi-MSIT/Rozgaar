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

from backend.fetchers.http_client import DEFAULT_TIMEOUT, get_json
from backend.fetchers.result import CollectionResult
from backend.core.location import parse_country
from backend.config.career_expansion import INDIA_BOARDS

INDIA_SCOPED_BOARDS = {"databricks", "roku", "gleanwork", "okta", "purestorage", "gitlab", "squarepointcapital", "quberesearchandtechnologies","alphagrepsecurities", "nksecuritiesresearch", "worldquant", "imc", "optiverus", "mongodb", "datadog"}
INDIA_SCOPED_BOARDS.update({"appian", "couchbaseinc", "inmobi", "typeface", "commvault", "sigmoid", "fanaticsinc", "fanaticscommerce", "fanaticsfbg", "fanaticscollectibles"})
INDIA_SCOPED_BOARDS.update({"sumologic", "observeai", "elastic", "cloudflare", "jfrog", "druva", "highradius", "harnessinc"})

log = logging.getLogger("jobbot")

# Kept as a module-level constant even though _get() itself now delegates
# to fetchers.http_client (which has its own internal default) — several
# other files import TIMEOUT directly from here (fetchers/oracle.py does,
# re-exporting it for debug scripts; see its own import line). Removing
# this during the http_client migration broke that import with an
# ImportError at startup — restoring it for backward compatibility.
TIMEOUT = DEFAULT_TIMEOUT

MAX_DESCRIPTION_CHARS = None  # Preserve source text unless a caller explicitly requests a limit.
# The three board adapters below explicitly retain full descriptions.

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "jobbot/1.0"
# collect() can make 16 Greenhouse/Lever/Ashby requests concurrently. Keep
# that many pooled connections instead of triggering urllib3's pool-full logs.
SESSION.mount("https://", HTTPAdapter(pool_connections=16, pool_maxsize=16, pool_block=True))

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_BREAK_RE = re.compile(r"</(p|div|li|br|h[1-6])\s*/?>", re.I)


def strip_html(text, max_chars=MAX_DESCRIPTION_CHARS):
    """Normalize source descriptions to text while keeping paragraph breaks.
    Converts block-level closing tags to newlines first so list items and
    paragraphs don't get smashed together with no separation, then strips
    remaining tags. Text is retained in full by default; callers can
    explicitly request max_chars for a bounded preview.

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
    if slug == "cloudflare":
        # The normal location says "In-Office"/"Hybrid", not a country.
        # Use the employer's geographic posting metadata, never that label.
        locations = [value for field in job.get("metadata") or []
                     if field.get("name") == "Job Posting Location"
                     for value in (field.get("value") if isinstance(field.get("value"), list) else [field.get("value")])
                     if isinstance(value, str) and re.search(r"\bIndia\b", value, re.I)]
        return "; ".join(locations) if locations else "Unknown"
    if slug in {"observeai", "jfrog"} and parse_country(location) != "India":
        locations = [office.get("location") or "" for office in job.get("offices") or []]
        india = [value for value in locations if parse_country(value) == "India"]
        if india:
            return "; ".join(india)
    if slug == "inmobi" and location.strip().lower() in {"bangalore", "bengaluru", "lucknow", "new delhi", "mumbai"}:
        location = location.strip()+", India"
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
    if slug in INDIA_BOARDS:
        if slug == "samsara" and re.fullmatch(r"Bengaluru - BLR\d+", location):
            location = "Bengaluru, India"
        offices = [office.get("location") or office.get("name") or "" for office in job.get("offices") or []]
        return _expansion_location(location, offices)
    return location


def _expansion_location(location, alternatives=(), country=None):
    """Retain positive India evidence; generic remote/unknown is not eligibility."""
    selected = []
    for value in [location, *alternatives]:
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        parsed = parse_country(value)
        # A country supplied by the ATS outranks ambiguous city/remote labels.
        if value == location and country:
            if str(country).strip().lower() in {"in", "ind", "india"}:
                if parsed != "India":
                    value += ", India"
            else:
                continue
        elif parsed != "India":
            # Only anchored city labels, never substring matches like Indiana.
            if parsed != "Unknown" or not re.fullmatch(r"(?:remote\s*[-–/]\s*)?(?:bengaluru|bangalore|gurugram|gurgaon|hyderabad|mumbai|chennai|pune|noida|new delhi|delhi)(?:\s*[,/-]\s*(?:karnataka|telangana|maharashtra|tamil nadu|haryana|uttar pradesh|ncr))?", value, re.I):
                continue
            value += ", India"
        if value not in selected:
            selected.append(value)
    return "; ".join(selected)


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
        if slug not in INDIA_SCOPED_BOARDS | INDIA_BOARDS or parse_country(_greenhouse_location(slug, j)) == "India"
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
    if slug in INDIA_BOARDS or slug == 'Sprinto':
        categories = job.get("categories") or {}
        return _expansion_location(categories.get("location") or "", categories.get("allLocations") or [], job.get("country"))
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
        if (slug in INDIA_BOARDS or slug == 'Sprinto') and not _lever_location(slug, j):
            continue
        if slug in {"ion", "coupa"} and (j.get("country") or "").upper() != "IN":
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


def _scoped_ashby_location(slug, job):
    location = _ashby_location(job)
    if slug in INDIA_BOARDS:
        address = ((job.get("address") or {}).get("postalAddress") or {})
        alternatives = [item.get("location") or "" for item in job.get("secondaryLocations") or [] if isinstance(item, dict)]
        return _expansion_location(location, alternatives, address.get("addressCountry"))
    if slug == "uipath":
        country = ((job.get("address") or {}).get("postalAddress") or {}).get("addressCountry")
        return location + ", India" if country in {"IN", "India"} else "Unknown"
    return location


def fetch_ashby(slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise RuntimeError(f"ashby board {slug}: missing jobs list")
    return [
        {
            "company": slug,
            "source_id": str(j.get("id", "")),
            "title": j["title"],
            "location": _scoped_ashby_location(slug, j),
            "url": j["jobUrl"],
            "description": strip_html(
                j.get("descriptionPlain", "") or j.get("description", ""), max_chars=None
            ),
        }
        for j in data.get("jobs", [])
        if slug not in {"confluent", "uipath"} | INDIA_BOARDS or parse_country(_scoped_ashby_location(slug, j)) == "India"
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
    company_results = {}
    def fetch_before_deadline(fn):
        if deadline is not None and time.monotonic() >= deadline:
            raise RuntimeError("shared collection deadline reached before board fetch")
        return fn()
    with ThreadPoolExecutor(max_workers=min(16, len(tasks))) as pool:
        futures = [(name, pool.submit(fetch_before_deadline, fn)) for name, fn in tasks]
        for name, f in futures:
            try:
                result = f.result()
                jobs += result
                company_results[name.split(":", 1)[1]] = {"status": "ok", "error": ""}
            except Exception as e:
                # A bug in one company's fetcher shouldn't take down the rest.
                log.exception("a company fetch failed: %s", e)
                failures += 1
                failed_boards.append(name)
                company_results[name.split(":", 1)[1]] = {"status": "failed", "error": str(e)[:300]}
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
        companies=company_results,
    )
