"""Find public ATS career feeds for candidate employer names.

Run on a machine with internet access:
    python -m scripts.career.discover_sources            # probe and write a report
    python -m scripts.career.discover_sources --apply     # register approved rows

Probes public Greenhouse, Lever, Ashby, SmartRecruiters and Workable endpoints with
slug variants of each name. A board is kept only when it lists at least one posting
with positive India evidence. Slug collisions with unrelated companies are possible,
so review the sample titles in the report, set "skip": true on wrong rows, then --apply.
Names with no match are listed for the user to supply careers links. Nothing here
checks fresher eligibility or pay.
"""
import argparse
import json
import re
import threading
import time
from collections import Counter
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from backend.fetchers.standard import _expansion_location

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "docs/catalog/CAREER_CANDIDATES_20261102.json"
RESULTS = ROOT / "docs/catalog/CAREER_DISCOVERY_20261102.json"
REPORT = ROOT / "docs/catalog/CAREER_DISCOVERY_20261102.md"
MODULE = ROOT / "backend/config/career_discovered.py"
LEGAL = {"inc", "ltd", "limited", "pvt", "private", "corp", "corporation", "plc", "the", "and"}
SOFT = {"india", "group", "technologies", "technology", "labs", "global", "services", "solutions", "company"}
ALL_GROUPS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable")
ENABLED = list(ALL_GROUPS[:4])  # Workable throttles unknown slugs, so it is opt-in (--workable)
URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
    "smartrecruiters": "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&country=in",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{slug}",
}
CAREER_URLS = {
    "greenhouse": "https://job-boards.greenhouse.io/{slug}",
    "lever": "https://jobs.lever.co/{slug}",
    "ashby": "https://jobs.ashbyhq.com/{slug}",
    "smartrecruiters": "https://careers.smartrecruiters.com/{slug}",
    "workable": "https://apply.workable.com/{slug}",
}


def slug_variants(name, hints=()):
    """Ordered, de-duplicated slug guesses; explicit hints come first."""
    base = re.sub(r"\([^)]*\)", " ", name.lower())
    named = [t for t in re.findall(r"[a-z0-9]+", base) if t not in LEGAL] or re.findall(r"[a-z0-9]+", base)
    core = [t for t in named if t not in SOFT] or named
    guesses = list(hints)
    guesses += ["".join(named), "-".join(named), "".join(core), "-".join(core), core[0],
                "".join(core) + "hq", "".join(t.capitalize() for t in core)]
    seen, result = set(), []
    for guess in guesses:
        if guess and guess not in seen:
            seen.add(guess)
            result.append(guess)
    return result[:8]


def india_postings(group, data):
    """Return (count, sample titles) of postings with India evidence for one ATS payload."""
    titles = []
    if group == "greenhouse":
        jobs = data.get("jobs") if isinstance(data, dict) else None
        for job in jobs or []:
            offices = [o.get("location") or o.get("name") or "" for o in job.get("offices") or []]
            if _expansion_location((job.get("location") or {}).get("name", ""), offices):
                titles.append(job.get("title", ""))
    elif group == "lever":
        for job in data if isinstance(data, list) else []:
            categories = job.get("categories") or {}
            if _expansion_location(categories.get("location") or "", categories.get("allLocations") or [], job.get("country")):
                titles.append(job.get("text", ""))
    elif group == "ashby":
        for job in (data.get("jobs") if isinstance(data, dict) else None) or []:
            loc = job.get("location")
            loc = loc.get("name", "") if isinstance(loc, dict) else (loc or "")
            address = ((job.get("address") or {}).get("postalAddress") or {})
            others = [i.get("location") or "" for i in job.get("secondaryLocations") or [] if isinstance(i, dict)]
            if _expansion_location(loc, others, address.get("addressCountry")):
                titles.append(job.get("title", ""))
    elif group == "smartrecruiters":
        for job in (data.get("content") if isinstance(data, dict) else None) or []:
            if str((job.get("location") or {}).get("country", "")).lower() == "in":
                titles.append(job.get("name", ""))
    elif group == "workable":
        for job in (data.get("jobs") if isinstance(data, dict) else None) or []:
            places = job.get("locations") or [{"country": job.get("country", ""), "city": job.get("city", "")}]
            if any((p.get("country_code") or p.get("countryCode") or "").upper() == "IN"
                   or str(p.get("country", "")).lower() == "india" for p in places):
                titles.append(job.get("title", ""))
    return len(titles), titles[:3]


HOST_GAP = {"apply.workable.com": 0.6, "api.lever.co": 0.3}  # Workable rate-limits bursts; Lever is slow
HOST_TIMEOUT = {"api.lever.co": 60}  # seconds; default 20
HOST_CONCURRENCY = {"api.lever.co": 3, "apply.workable.com": 2}  # simultaneous requests per host
_slots = {}
DEFAULT_GAP = 0.1
_gate_lock, _next_slot = threading.Lock(), {}
PROBLEMS = Counter()  # (host, reason) -> failed requests, reported at the end of a run


def _wait_turn(url):
    """Space requests per host across threads so one ATS is not hammered."""
    host = urlsplit(url).netloc
    gap = HOST_GAP.get(host, DEFAULT_GAP)
    with _gate_lock:
        now = time.monotonic()
        slot = max(now, _next_slot.get(host, 0.0))
        _next_slot[host] = slot + gap
    if slot > now:
        time.sleep(slot - now)


def fetch(session, url, attempts=3):
    """Return ("ok", json), ("missing", None) for a clean 4xx/non-JSON, or ("error", None).

    A rate limit (429), server error or timeout is "error", never "missing", so a busy ATS
    cannot make an existing board look absent."""
    host = urlsplit(url).netloc
    slot = _slots.setdefault(host, threading.BoundedSemaphore(HOST_CONCURRENCY.get(host, 8)))
    for attempt in range(attempts):
        _wait_turn(url)
        try:
            with slot:
                response = session.get(url, timeout=HOST_TIMEOUT.get(host, 20))
        except requests.RequestException as exc:
            PROBLEMS[(host, type(exc).__name__)] += 1
            time.sleep(2 * (attempt + 1))
            continue
        if response.status_code == 429 or response.status_code >= 500:
            PROBLEMS[(host, f"HTTP {response.status_code}")] += 1
            try:
                wait = float(response.headers.get("Retry-After", ""))
            except ValueError:
                wait = 3 * (attempt + 1)
            time.sleep(min(wait, 20))
            continue
        if response.status_code != 200:
            return "missing", None
        try:
            return "ok", response.json()
        except ValueError:
            return "missing", None
    return "error", None


def check_hosts():
    """One request per ATS against a board known to exist; shows which host is unreachable."""
    samples = {"greenhouse": "airbnb", "lever": "palantir", "ashby": "atlan",
               "smartrecruiters": "TheNielsenCompany", "workable": "amagi"}
    with requests.Session() as session:
        session.headers["User-Agent"] = "jobbot/1.0"
        for group, slug in samples.items():
            url = URLS[group].format(slug=slug)
            started = time.monotonic()
            try:
                response = session.get(url, timeout=20)
                result = f"HTTP {response.status_code}"
            except requests.RequestException as exc:
                result = type(exc).__name__
            print(f"{group:16} {urlsplit(url).netloc:28} {result:22} {time.monotonic() - started:.1f}s", flush=True)


def probe(session, candidate):
    """(row, errors): first ATS/slug with India postings, else (None, number of failed requests)."""
    slugs = slug_variants(candidate["name"], candidate.get("slugs") or ())
    errors = 0
    for group in candidate.get("groups") or ENABLED:
        for slug in (slugs[:3] if group == "workable" else slugs):
            state, data = fetch(session, URLS[group].format(slug=slug))
            if state == "error":
                errors += 1
                continue
            if state != "ok" or not data:
                continue
            count, titles = india_postings(group, data)
            if count:
                return {"key": slug, "name": candidate["name"], "group": group,
                        "career_url": CAREER_URLS[group].format(slug=slug),
                        "india_postings": count, "sample_titles": titles, "skip": False}, errors
    return None, errors


def existing_keys():
    from backend.config import sources
    keys = set()
    for name in ("GREENHOUSE", "LEVER", "ASHBY", "WORKABLE", "SMARTRECRUITERS"):
        for item in getattr(sources, name):
            keys.add((item.get("company_id") if isinstance(item, dict) else item).lower())
    names = {n.lower() for n in sources.DISPLAY_NAMES.values()}
    return keys, names


def discover(candidates, workers=8, only=None, progress=False):
    """Returns (found, missing, already, inconclusive). Inconclusive names had failed requests
    (rate limit/timeouts) and no match, so a retry may still find them."""
    keys, names = existing_keys()
    found, missing, already, inconclusive = [], [], [], []
    todo = [c for c in candidates if not only or only.lower() in c["name"].lower()]
    already.extend(c["name"] for c in todo if c["name"].lower() in names)
    todo = [c for c in todo if c["name"] not in already]
    with requests.Session() as session, ThreadPoolExecutor(max_workers=workers) as pool:
        session.headers["User-Agent"] = "jobbot/1.0"
        for number, (candidate, (row, errors)) in enumerate(zip(todo, pool.map(lambda c: probe(session, c), todo)), 1):
            if row and row["key"].lower() in keys:
                already.append(candidate["name"])
                outcome = "already configured"
            elif row:
                found.append(row)
                outcome = f"FOUND {row['group']}/{row['key']} ({row['india_postings']} India)"
            elif errors:
                inconclusive.append(candidate["name"])
                outcome = "retry needed"
            else:
                missing.append(candidate["name"])
                outcome = "not found"
            if progress:
                print(f"[{number}/{len(todo)}] {candidate['name']}: {outcome}", flush=True)
                if number % 10 == 0 and PROBLEMS:
                    print("   problems so far: " + "; ".join(f"{h} {r} x{c}" for (h, r), c in sorted(PROBLEMS.items())), flush=True)
    return found, missing, already, inconclusive


def write_report(found, missing, already, inconclusive=()):
    RESULTS.write_text(json.dumps({"found": found, "not_found": missing, "inconclusive": list(inconclusive),
                                   "already_configured": already},
                                  indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Career source discovery, 2 November 2026", "",
             "Public ATS feeds with positive India evidence. Slug collisions are possible: check the sample titles, "
             "set `\"skip\": true` in the JSON for wrong rows, then run `--apply`. Registration does not imply fresher "
             "eligibility or pay.", "",
             f"Found {len(found)}, not found {len(missing)}, retry needed {len(inconclusive)}, already configured {len(already)}.", "",
             "| Company | ATS | India postings | Sample titles | Page |", "|---|---|---:|---|---|"]
    for row in found:
        lines.append(f"| {row['name']} | {row['group']} | {row['india_postings']} | "
                     f"{'; '.join(row['sample_titles']).replace('|', '/')} | {row['career_url']} |")
    lines += ["", "## Not found: send careers links", ""] + [f"- {name}" for name in missing]
    if inconclusive:
        lines += ["", "## Retry needed (rate limit or timeout; run with --retry)", ""] + [f"- {name}" for name in inconclusive]
    if already:
        lines += ["", "## Already configured", ""] + [f"- {name}" for name in already]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_results():
    rows = [r for r in json.loads(RESULTS.read_text(encoding="utf-8"))["found"] if not r.get("skip")]
    keys, _ = existing_keys()
    # Already-registered rows are kept so a repeat --apply is idempotent.
    own = {r["key"].lower() for r in json.loads(RESULTS.read_text(encoding="utf-8"))["found"]}
    rows = [r for r in rows if r["key"].lower() not in keys or r["key"].lower() in own]
    body = [{k: r[k] for k in ("key", "name", "group", "career_url")} for r in rows]
    text = MODULE.read_text(encoding="utf-8")
    head, rest = text.split("SOURCES = ", 1)
    tail = rest[rest.index("\nINDIA_BOARDS"):]
    MODULE.write_text(head + "SOURCES = " + json.dumps(body, indent=1, ensure_ascii=False).replace(": true", ": True") + "\n" + tail,
                      encoding="utf-8")
    return len(body)


def retry_inconclusive(workers):
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    names = set(data.get("inconclusive", []))
    candidates = [c for c in json.loads(CANDIDATES.read_text(encoding="utf-8")) if c["name"] in names]
    found, missing, already, inconclusive = discover(candidates, workers, progress=True)
    data["found"] += found  # earlier rows keep any "skip" edits
    data["not_found"] += missing
    data["already_configured"] += already
    return data["found"], data["not_found"], data["already_configured"], inconclusive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--candidates", type=Path, default=CANDIDATES)
    parser.add_argument("--only", help="probe only names containing this text")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--workable", action="store_true", help="also probe Workable (slow; it rate-limits unknown slugs)")
    parser.add_argument("--check", action="store_true", help="test reachability of each ATS host and exit")
    parser.add_argument("--retry", action="store_true", help="re-probe names that hit rate limits or timeouts")
    parser.add_argument("--apply", action="store_true", help="write approved rows to backend/config/career_discovered.py")
    args = parser.parse_args(argv)
    if args.workable:
        ENABLED.append("workable")
    if args.check:
        check_hosts()
        return
    if args.apply:
        print(f"registered {apply_results()} sources in {MODULE.relative_to(ROOT)}")
        return
    if args.retry:
        result = retry_inconclusive(args.workers)
    else:
        candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
        result = discover(candidates, args.workers, args.only, progress=True)
    found, missing, already, inconclusive = result
    for (host, reason), count in sorted(PROBLEMS.items()):
        print(f"request problems: {host}: {reason} x{count}")
    write_report(found, missing, already, inconclusive)
    print(f"found {len(found)}, not found {len(missing)}, retry needed {len(inconclusive)}, "
          f"already configured {len(already)}; see {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
