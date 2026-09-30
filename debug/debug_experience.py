"""
Diagnostic for core/experience.py's extraction — shows exactly what's
STORED in jobs.db for a given job vs. what extract_min_experience()
computes RIGHT NOW against that exact stored text. The two can differ
for a legitimate reason: process_backlog() only ever reprocesses rows
where experience_years IS NULL, so a row processed under an OLDER
version of the extraction logic keeps that old value until
--reprocess-experience (or a code change that resets it) forces a
re-derive. This script tells you definitively which situation you're
in, instead of guessing:

  STORED == FRESH   -> not a stale-data issue. If the value still looks
                        wrong, it's a genuine bug in the current logic —
                        paste the printed description back for a fix.
  STORED != FRESH    -> stale data. Run `python run.py --reprocess-experience`
                        to bring every row up to date with the current logic.

Usage:
  python debug/debug_experience.py "business analyst"     search title/company
  python debug/debug_experience.py --id fractal:12345      look up by exact id
  python debug/debug_experience.py --all-mismatches        scan the WHOLE db,
                                                             print only rows
                                                             where stored !=
                                                             fresh (can be slow
                                                             on a large db)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlite3

from core.experience import extract_min_experience

DB_PATH = "db/jobs.db"


def describe(exp_years):
    if exp_years is None:
        return "NULL (not yet processed)"
    if exp_years == -1:
        return "-1 (processed, nothing found)"
    return str(exp_years)


def show_job(row):
    jid, company, title, description, stored = row
    fresh = extract_min_experience(f"{title} {description or ''}")
    fresh_stored_form = -1 if fresh is None else fresh  # match the DB's sentinel convention

    print(f"--- {jid} ---")
    print(f"company:  {company}")
    print(f"title:    {title}")
    print(f"stored experience_years: {describe(stored)}")
    print(f"FRESH extraction result: {describe(fresh_stored_form)}")
    if stored != fresh_stored_form:
        print("=> MISMATCH — this row has a stale value from an older version")
        print("   of the extraction logic. Run: python run.py --reprocess-experience")
    else:
        print("=> matches — not a stale-data issue.")
        if fresh_stored_form == -1 or (fresh_stored_form is not None and fresh_stored_form > 0):
            print("   If this value still looks wrong for what the description")
            print("   actually says, it's a genuine bug in core/experience.py's")
            print("   current logic, not a caching/staleness problem.")
    print()
    print("--- description (as stored, first 800 chars) ---")
    print((description or "")[:800])
    print()
    print("=" * 70)
    print()


def main():
    resolved_path = os.path.abspath(DB_PATH)
    exists = os.path.exists(resolved_path)
    print(f"Using DB_PATH: {DB_PATH}  (resolved: {resolved_path})")
    print(f"File exists: {exists}")
    if not exists:
        print("!! This file doesn't exist yet. Run `python run.py` first.")
    print()

    conn = sqlite3.connect(DB_PATH)

    if "--all-mismatches" in sys.argv:
        rows = conn.execute(
            "SELECT id, company, title, description, experience_years FROM jobs"
        ).fetchall()
        print(f"Scanning {len(rows)} row(s) for stale experience_years values...\n")
        mismatches = 0
        for jid, company, title, description, stored in rows:
            fresh = extract_min_experience(f"{title} {description or ''}")
            fresh_stored_form = -1 if fresh is None else fresh
            if stored != fresh_stored_form:
                mismatches += 1
                show_job((jid, company, title, description, stored))
        print(f"Done. {mismatches}/{len(rows)} row(s) had a stale value.")
        if mismatches:
            print("Run: python run.py --reprocess-experience")
        return

    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        if idx + 1 >= len(sys.argv):
            print("usage: python debug/debug_experience.py --id <exact job id>")
            sys.exit(1)
        target_id = sys.argv[idx + 1]
        row = conn.execute(
            "SELECT id, company, title, description, experience_years FROM jobs WHERE id = ?",
            (target_id,),
        ).fetchone()
        if not row:
            print(f"No job found with id={target_id!r}")
            sys.exit(1)
        show_job(row)
        return

    # Default: search by title/company substring
    search_terms = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not search_terms:
        print(__doc__)
        sys.exit(1)
    query = " ".join(search_terms)
    rows = conn.execute(
        "SELECT id, company, title, description, experience_years FROM jobs "
        "WHERE title LIKE ? OR company LIKE ? LIMIT 20",
        (f"%{query}%", f"%{query}%"),
    ).fetchall()
    if not rows:
        print(f"No jobs found matching {query!r}")
        sys.exit(1)
    print(f"Found {len(rows)} matching job(s) (showing up to 20):\n")
    for row in rows:
        show_job(row)


if __name__ == "__main__":
    main()
