"""
Show historical per-platform run stats — which ATS produces useful jobs,
which is slow, which rarely matches.

Usage:
  python stats.py                latest run, per platform
  python stats.py --all          full history, every run
  python stats.py --summary      totals per platform across all runs
  python stats.py --health       latest status and abnormal volume drops
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import config
from core.source_health import summarize

DB_PATH = str(Path(__file__).resolve().parent / "db" / "jobs.db")

if not Path(DB_PATH).exists():
    raise SystemExit("No jobs database yet — run python run.py first.")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row


def fmt_ts(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def yield_pct(saved, fetched):
    return round(100 * saved / fetched, 1) if fetched else 0.0


if "--health" in sys.argv:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(run_stats)")}
    if not columns:
        print("No run_stats recorded yet — run python run.py at least once first.")
    else:
        error_field = "error" if "error" in columns else "NULL AS error"
        status_field = "status" if "status" in columns else "'ok' AS status"
        rows = conn.execute(
            "SELECT id, platform, timestamp, jobs_fetched, jobs_saved, "
            f"{status_field}, {error_field} FROM run_stats ORDER BY timestamp DESC, id DESC"
        ).fetchall()
        if not rows:
            print("No run_stats recorded yet — run python run.py at least once first.")
        else:
            print("Fetch health by platform (baseline: up to 7 earlier successful nonzero runs)")
            disabled = {"workable"} if not config.WORKABLE else set()
            for item in summarize(rows, disabled_platforms=disabled):
                latest = item["latest"]
                baseline = f"{item['baseline']:.0f}" if item["baseline"] is not None else "—"
                last_ok = (
                    "n/a" if item["health"] == "not configured"
                    else fmt_ts(item["last_success"]) if item["last_success"] else "never"
                )
                print(
                    f"{item['platform']:<18} {item['health']:<18} "
                    f"fetched={latest['jobs_fetched']:<6} saved={latest['jobs_saved']:<5} "
                    f"baseline={baseline:<5} last={fmt_ts(latest['timestamp'])} "
                    f"last_ok={last_ok}"
                )
                if latest["error"]:
                    print(f"  reason: {latest['error'][:300]}")
            print("A successful fetch is not proof that every listing is current or that a source was complete.")

elif "--summary" in sys.argv:
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
