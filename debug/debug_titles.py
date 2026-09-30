"""
Show which jobs matched (and why) without flooding the terminal with every
non-matching posting. Full per-job detail always gets written to a log file
you can open when you actually need to dig in.

Run from the project root:
  python debug/debug_titles.py              matches-only + full detail to debug_log.txt
  python debug/debug_titles.py --all        everything in terminal too
  python debug/debug_titles.py --company groww   only that company's rows
"""

import sys
import os

# Allow `import config`, `import core...` when run as `python debug/debug_titles.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Windows' default console encoding (cp1252) can't print some Unicode
# characters that show up in real job titles (narrow no-break spaces, en
# dashes, etc.) — force UTF-8 so this doesn't crash mid-run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config
from core.collector import collect_all
from core.filters import matches

SHOW_ALL = "--all" in sys.argv
FILTER_COMPANY = None
if "--company" in sys.argv:
    i = sys.argv.index("--company")
    if i + 1 < len(sys.argv):
        FILTER_COMPANY = sys.argv[i + 1]

LOG_PATH = "debug_log.txt"

jobs, failed_platforms = collect_all()
print(f"total postings fetched: {len(jobs)}")
if failed_platforms:
    print(f"WARNING: platform(s) failed and are NOT included above: {', '.join(failed_platforms)}")

match_count = 0
company_counts = {}

with open(LOG_PATH, "w", encoding="utf-8") as log:
    log.write(f"total postings fetched: {len(jobs)}\n")
    if failed_platforms:
        log.write(f"WARNING: platform(s) failed and are NOT included above: {', '.join(failed_platforms)}\n")
    log.write("\n")
    for j in jobs:
        title = j.get("title", "")
        company = j.get("company", "")
        loc = j.get("location") or ""
        desc = j.get("description", "")
        company_counts[company] = company_counts.get(company, 0) + 1

        inc_title = bool(config.INCLUDE.search(title))
        inc_desc = bool(config.INCLUDE.search(f"{title} {desc}"))
        exc = bool(config.EXCLUDE_SENIOR.search(title))  # the filter matches()
        # actually applies — config.EXCLUDE is a legacy/unused regex kept
        # only so this script has something to display; showing it here
        # was misleading (e.g. it flags "architect" as exc=True even though
        # the real filter doesn't).
        locmatch = bool(config.LOCATION.search(loc))
        relevance = config.RELEVANCE_FILTERS.get(company)
        rel_ok = (relevance is None) or bool(relevance.search(title))
        ok = matches(j)

        flag = "MATCH" if ok else "     "
        via = "title" if inc_title else ("desc " if inc_desc else "-----")
        rel_tag = "" if relevance is None else f" rel={rel_ok}"
        line = (f"[{flag}] via={via} {company:<10} {title[:50]:<50} | {loc[:22]:<22} "
                f"exc={exc} loc={locmatch}{rel_tag}")

        # Full detail always goes to the log file, regardless of flags.
        log.write(line + "\n")
        if ok:
            log.write(f"         -> {j['url']}\n")
            match_count += 1

        # Terminal output is filtered by default.
        if FILTER_COMPANY and company != FILTER_COMPANY:
            continue
        if SHOW_ALL or FILTER_COMPANY or ok:
            print(line)
            if ok:
                print(f"         -> {j['url']}")

print(f"\n{match_count} matches out of {len(jobs)} postings")
print("per-company counts:", ", ".join(f"{c}={n}" for c, n in sorted(company_counts.items())))
print(f"full detail (every posting, matched or not) written to {LOG_PATH}")
