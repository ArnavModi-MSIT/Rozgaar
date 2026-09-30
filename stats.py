"""
Show historical per-platform run stats — which ATS produces useful jobs,
which is slow, which rarely matches.

Usage:
  python stats.py                latest run, per platform
  python stats.py --all          full history, every run
  python stats.py --summary      totals per platform across all runs
"""

import sqlite3
import sys
from datetime import datetime

DB_PATH = "db/jobs.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row


def fmt_ts(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def yield_pct(saved, fetched):
    return round(100 * saved / fetched, 1) if fetched else 0.0


if "--summary" in sys.argv:
    rows = conn.execute(
        """SELECT platform,
                  COUNT(*) as runs,
                  SUM(jobs_fetched) as total_fetched,
                  SUM(jobs_matched) as total_matched,
                  SUM(jobs_saved) as total_saved,
                  AVG(runtime_seconds) as avg_runtime
           FROM run_stats GROUP BY platform ORDER BY total_saved DESC"""
    ).fetchall()
    print(f"{'platform':<16} {'runs':>5} {'fetched':>8} {'matched':>8} {'saved':>7} "
          f"{'yield%':>7} {'avg_sec':>8}")
    for r in rows:
        y = yield_pct(r['total_saved'], r['total_fetched'])
        print(f"{r['platform']:<16} {r['runs']:>5} {r['total_fetched']:>8} "
              f"{r['total_matched']:>8} {r['total_saved']:>7} {y:>6}% {r['avg_runtime']:>8.1f}")

elif "--all" in sys.argv:
    rows = conn.execute(
        "SELECT * FROM run_stats ORDER BY timestamp DESC"
    ).fetchall()
    for r in rows:
        status = r['status'] if 'status' in r.keys() else 'ok'
        flag = "" if status == "ok" else f" [{status}]"
        print(f"{fmt_ts(r['timestamp'])} {r['platform']:<16} "
              f"fetched={r['jobs_fetched']:<6} matched={r['jobs_matched']:<5} "
              f"saved={r['jobs_saved']:<4} runtime={r['runtime_seconds']}s{flag}")

else:
    latest_run_id = conn.execute("SELECT MAX(run_id) FROM run_stats").fetchone()[0]
    if latest_run_id is None:
        print("No run_stats recorded yet — run run.py at least once first.")
    else:
        rows = conn.execute(
            "SELECT * FROM run_stats WHERE run_id = ? ORDER BY jobs_saved DESC",
            (latest_run_id,),
        ).fetchall()
        print(f"latest run: {fmt_ts(latest_run_id / 1000 if latest_run_id > 10**12 else latest_run_id)}\n")
        for r in rows:
            status = r['status'] if 'status' in r.keys() else 'ok'
            flag = "" if status == "ok" else f" [{status}]"
            print(f"{r['platform']:<16} fetched={r['jobs_fetched']:<6} "
                  f"matched={r['jobs_matched']:<5} saved={r['jobs_saved']:<4} "
                  f"runtime={r['runtime_seconds']}s{flag}")

conn.close()
