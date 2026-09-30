import sqlite3
import unittest
from unittest.mock import patch

import config
from core.collector import PLATFORMS
from core.source_health import summarize
from core.storage import init_db, record_stats


class SourceHealthTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        init_db(self.conn)

    def tearDown(self):
        self.conn.close()

    def history(self, counts, *, latest_status="ok", latest_error=None):
        for run_id, count in enumerate(counts, start=1):
            status = latest_status if run_id == len(counts) else "ok"
            error = latest_error if run_id == len(counts) else None
            record_stats(self.conn, run_id, "example", count, count, 0, 1.0, status=status, error=error)
        rows = self.conn.execute("SELECT * FROM run_stats ORDER BY id DESC").fetchall()
        return summarize(rows)[0]

    def test_large_drop_uses_prior_successes(self):
        result = self.history([100, 90, 110, 20])
        self.assertEqual(result["health"], "large drop")
        self.assertEqual(result["baseline"], 100)

    def test_failed_run_does_not_become_zero_success(self):
        result = self.history([100, 90, 110, 0], latest_status="failed", latest_error="timeout")
        self.assertEqual(result["health"], "failed")
        self.assertEqual(result["latest"]["error"], "timeout")
        self.assertIsNotNone(result["last_success"])

    def test_zero_after_history_and_partial(self):
        self.assertEqual(self.history([100, 90, 110, 0])["health"], "zero after history")
        self.conn.execute("DELETE FROM run_stats")
        self.assertEqual(self.history([100, 90, 110, 20], latest_status="partial")["health"], "partial")

    def test_existing_schema_gains_error_column(self):
        old = sqlite3.connect(":memory:")
        old.execute("CREATE TABLE run_stats (id INTEGER PRIMARY KEY, run_id INTEGER, timestamp INTEGER, platform TEXT, jobs_fetched INTEGER, jobs_matched INTEGER, jobs_saved INTEGER, runtime_seconds REAL, status TEXT)")
        init_db(old)
        columns = {row[1] for row in old.execute("PRAGMA table_info(run_stats)")}
        self.assertIn("error", columns)
        old.close()

    def test_unconfigured_workable_is_skipped(self):
        collect_workable = next(fn for name, fn in PLATFORMS if name == "workable")
        with patch.object(config, "WORKABLE", []):
            result = collect_workable(None)
        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.error, "no Workable boards configured")

        record_stats(self.conn, 1, "workable", 0, 0, 0, 0.0, status="ok")
        rows = self.conn.execute("SELECT * FROM run_stats").fetchall()
        self.assertEqual(summarize(rows, disabled_platforms={"workable"})[0]["health"], "not configured")


if __name__ == "__main__":
    unittest.main()
