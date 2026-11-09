"""Re-fetch Wipro descriptions that are empty or only the company boilerplate.

Older collections stored Wipro's "About Wipro" paragraph (or nothing, when the
time budget ran out) instead of the job text. Dry run by default:

    python -m scripts.career.repair_wipro_descriptions            # report only
    python -m scripts.career.repair_wipro_descriptions --apply    # back up, then update

Updated rows get category/skills/experience reset so the next collection run
(or its process-only step) re-derives them from the real description.
"""
import argparse
import shutil
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from backend.core.storage import update_descriptions
from backend.fetchers.successfactors import _BOILERPLATE_PREFIXES, fetch_job_description
from rojgaar.paths import CAREER_DB

HOST = "careers.wipro.com"


def broken_rows(conn):
    rows = conn.execute(
        "SELECT id, url, COALESCE(description, '') FROM jobs WHERE lower(company) = 'wipro'").fetchall()
    return [(jid, url) for jid, url, desc in rows
            if not desc.strip() or desc.lstrip().startswith(_BOILERPLATE_PREFIXES)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(CAREER_DB))
    ap.add_argument("--apply", action="store_true", help="write changes (a backup copy is made first)")
    ap.add_argument("--limit", type=int, default=0, help="only look at the first N broken rows")
    args = ap.parse_args(argv)

    conn = sqlite3.connect(args.db)
    todo = broken_rows(conn)
    if args.limit:
        todo = todo[:args.limit]
    print(f"{len(todo)} Wipro row(s) with an empty or boilerplate description")
    with ThreadPoolExecutor(max_workers=2) as pool:
        texts = list(pool.map(lambda r: fetch_job_description(HOST, urlparse(r[1]).path), todo))
    fixed = [(jid, text) for (jid, _), text in zip(todo, texts) if text]
    print(f"fetched a real description for {len(fixed)}; {len(todo) - len(fixed)} still empty (page gone or no text)")
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return 0
    if fixed:
        backup = f"{args.db}.before-wipro-descriptions-{time.strftime('%Y%m%d-%H%M%S')}"
        conn.close()
        shutil.copy2(args.db, backup)
        print(f"backup: {backup}")
        conn = sqlite3.connect(args.db)
        update_descriptions(conn, fixed)
        print(f"updated {len(fixed)} row(s)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
