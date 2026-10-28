"""Separate-pipeline and JSON-batch checks using synthetic local data only."""
from contextlib import ExitStack
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.api import data, main
from backend.api.platform import get_service
from backend.core.pipelines import PlatformService
from backend.core.reader_bridge import READER_ROOT, reader_modules
from backend.core.separate_pipelines import separate_pipelines
from backend.core.storage import init_db


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.db, self.folder = self.root / "jobs.db", self.root / "reader"
        self.folder.mkdir()
        for name, value in (("DB_PATH", str(self.db)), ("_initialized_db_paths", set()),
                            ("_jobs_cache", dict(df=None, loaded_at=0)),
                            ("_resume", dict(key=None, text="", skills=set(), scores={}, explanations={}, pool_key=None,
                                             filename=None, embedding=None, embedding_key=None))):
            self.stack.enter_context(patch.object(data, name, value))
        with sqlite3.connect(self.db) as conn: init_db(conn)
        self.service = PlatformService(self.db, self.folder, data.invalidate_jobs)
        main.app.dependency_overrides[get_service] = lambda: self.service
        self.addCleanup(main.app.dependency_overrides.clear)
        self.client = self.stack.enter_context(TestClient(main.app))
        self.headers = {"X-Platform-Token": self.service.token}

    def add_jobs(self, count=1, start=0, source="standard", description="Required qualifications: SQL and Python."):
        ids = [f"{source}:{index}" for index in range(start, start + count)]
        with sqlite3.connect(self.db) as conn:
            conn.executemany("""INSERT INTO jobs(id,company,title,location,url,description,source,first_seen,last_seen,skills)
                VALUES(?,?,?,?,?,?,?,?,?,?)""", [(jid, "fixture", f"Data Intern {jid}", "Delhi, India",
                    "https://example.com/jobs/" + jid, description, source, 1000 + index, 1000 + index, "sql,python") for index, jid in enumerate(ids)])
        data.invalidate_jobs()
        return ids

    def rows(self, sql="SELECT * FROM jobs"):
        with sqlite3.connect(self.db) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql)]

    def export(self, ids, **extra):
        return self.client.post("/api/platform/career-exports", json={"ids": ids, **extra}, headers=self.headers)

    def remove(self, batch_id):
        return self.client.post(f"/api/platform/career-exports/{batch_id}/remove", json={}, headers=self.headers)

    def test_export_preserves_exact_selected_order_and_full_descriptions(self):
        text = "SQL responsibilities.\n" * 4000
        ids = self.add_jobs(120, description=text)
        selected = list(reversed(ids[10:110]))
        result = self.export(selected, filters={"search": "Data", "hideExported": False})
        self.assertEqual(result.status_code, 200, result.text)
        value = result.json()
        self.assertEqual(value["count"], 100)
        self.assertEqual([job["id"] for job in value["jobs"]], selected)
        self.assertEqual(value["jobs"][0]["description"], text)
        self.assertEqual(value["selection"]["filters"]["search"], "Data")
        self.assertIn("attachment", result.headers["content-disposition"])
        self.assertTrue(all(row["dismissed"] == 0 for row in self.rows()))

    def test_remove_hides_only_that_batch_and_is_reversible(self):
        ids = self.add_jobs(130)
        batch = self.export(ids[:100]).json()
        # A later list refresh or another JSON batch cannot change membership.
        self.export(ids[100:])
        self.client.get("/api/jobs")
        result = self.remove(batch["batch_id"]).json()
        self.assertEqual(result["ids"], ids[:100])
        self.assertEqual(result["removed"], 100)
        rows = {row["id"]: row for row in self.rows()}
        self.assertTrue(all(rows[jid]["dismissed"] == 1 for jid in ids[:100]))
        self.assertTrue(all(rows[jid]["dismissed"] == 0 for jid in ids[100:]))
        self.client.post("/api/restore", json={"ids": result["ids"]})
        self.assertTrue(all(row["dismissed"] == 0 for row in self.rows()))

    def test_repeat_remove_does_not_restore_or_remove_unrelated_jobs(self):
        ids = self.add_jobs(5)
        batch = self.export(ids[:2]).json()
        self.assertEqual(self.remove(batch["batch_id"]).json()["removed"], 2)
        self.assertEqual(self.remove(batch["batch_id"]).json()["ids"], [])
        self.assertEqual(len(self.client.get("/api/jobs").json()["jobs"]), 3)

    def test_download_again_is_a_snapshot_after_source_content_changes(self):
        ids = self.add_jobs()
        payload = self.export(ids).json()
        with sqlite3.connect(self.db) as conn: conn.execute("UPDATE jobs SET description='Changed source'")
        repeated = self.client.get("/api/platform/career-exports/" + payload["batch_id"])
        self.assertEqual(repeated.json(), payload)

    def test_export_marks_items_for_hide_exported_filter_without_removing_them(self):
        ids = self.add_jobs(3)
        self.export(ids[:2])
        rows = {row["id"]: row for row in self.client.get("/api/jobs").json()["jobs"]}
        self.assertTrue(rows[ids[0]]["exported"])
        self.assertFalse(rows[ids[2]]["exported"])
        self.assertEqual(len(rows), 3)

    def test_latest_batch_persists_and_tracks_undo(self):
        ids = self.add_jobs(3)
        batch = self.export(ids).json()
        latest = self.client.get("/api/platform/state").json()["latest_export"]
        self.assertEqual(latest["batch_id"], batch["batch_id"])
        self.assertEqual(latest["remaining_count"], 3)
        result = self.remove(batch["batch_id"]).json()
        self.assertEqual(self.client.get("/api/platform/state").json()["latest_export"]["remaining_count"], 0)
        self.client.post("/api/restore", json={"ids": result["ids"]})
        self.assertEqual(self.client.get("/api/platform/state").json()["latest_export"]["remaining_count"], 3)

    def test_export_rejects_empty_duplicate_oversized_missing_and_hidden_ids(self):
        ids = self.add_jobs(1001)
        self.assertEqual(self.export([]).status_code, 422)
        self.assertEqual(self.export(ids).status_code, 422)
        self.assertEqual(self.export([ids[0], ids[0]]).status_code, 409)
        self.assertEqual(self.export(["not-here"]).status_code, 409)
        self.client.post(f"/api/jobs/{ids[0]}/dismiss")
        self.assertEqual(self.export([ids[0]]).status_code, 409)
        self.assertFalse(self.rows("SELECT * FROM career_exports"))

    def test_adjustable_batch_sizes_preserve_order_metadata_and_exact_removal(self):
        ids = self.add_jobs(1001)
        for limit in (50, 100, 250, 500, 1000):
            with self.subTest(limit=limit):
                selected = list(reversed(ids[:limit]))
                response = self.export(selected, limit=limit)
                self.assertEqual(response.status_code, 200, response.text)
                value = response.json()
                self.assertEqual(value["count"], limit)
                self.assertEqual(value["selection"]["limit"], limit)
                self.assertEqual([j["id"] for j in value["jobs"]], selected)
        result = self.remove(value["batch_id"]).json()
        self.assertEqual(result["ids"], selected)
        self.assertEqual(result["removed"], 1000)
        self.assertEqual([r["id"] for r in self.rows("SELECT * FROM jobs WHERE dismissed=0")], ids[1000:])
        self.client.post("/api/restore", json={"ids": result["ids"]})
        self.assertEqual(len(self.rows("SELECT * FROM jobs WHERE dismissed=0")), 1001)

    def test_selected_limit_allows_fewer_jobs_but_rejects_overflow_and_unsupported_size(self):
        ids = self.add_jobs(51)
        small = self.export(ids[:7], limit=500)
        self.assertEqual(small.status_code, 200)
        self.assertEqual(small.json()["count"], 7)
        self.assertEqual(small.json()["selection"]["limit"], 500)
        self.assertEqual(self.export(ids, limit=50).status_code, 409)
        self.assertEqual(self.export(ids[:1], limit=200).status_code, 422)

    def test_reader_records_never_appear_in_career_list_or_exports(self):
        career = self.add_jobs()
        reader = self.add_jobs(source="reader_linkedin")
        jobs = self.client.get("/api/jobs").json()["jobs"]
        self.assertEqual([job["id"] for job in jobs], career)
        self.assertEqual(self.export(reader).status_code, 409)

    def test_missing_description_and_unknown_experience_are_explicit(self):
        ids = self.add_jobs(description="")
        record = self.export(ids).json()["jobs"][0]
        self.assertEqual(record["description_status"], "missing")
        self.assertEqual(record["required_experience_years"], -1)

    def test_json_does_not_include_private_notes_or_resume_text(self):
        ids = self.add_jobs()
        with sqlite3.connect(self.db) as conn: conn.execute("UPDATE jobs SET notes='private-note-fixture'")
        payload = self.export(ids).json()
        self.assertNotIn("private-note-fixture", json.dumps(payload))
        self.assertNotIn("notes", payload["jobs"][0])

    def test_mutations_require_token_and_local_origin(self):
        ids = self.add_jobs()
        self.assertEqual(self.client.post("/api/platform/career-exports", json={"ids": ids}).status_code, 403)
        self.assertEqual(self.client.post("/api/platform/career-exports", json={"ids": ids}, headers={**self.headers, "Origin": "https://foreign.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/platform/sync", json={}, headers=self.headers).status_code, 410)
        self.assertEqual(self.remove("missing").status_code, 404)

    def test_separation_archives_reader_rows_and_preserves_all_career_fields(self):
        self.add_jobs(3)
        self.add_jobs(2, source="reader_linkedin")
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE jobs SET notes='keep history',tracking_status='applied',dismissed=1")
        career_before = self.rows("SELECT * FROM jobs WHERE source='standard'")
        reader_before = self.rows("SELECT * FROM jobs WHERE source='reader_linkedin'")
        result = separate_pipelines(self.db, self.folder)
        self.assertEqual(result["archived"], 2)
        self.assertEqual(self.rows(), career_before)
        with sqlite3.connect(result["archive"]) as conn:
            conn.row_factory = sqlite3.Row
            self.assertEqual([dict(row) for row in conn.execute("SELECT * FROM jobs")], reader_before)
        with sqlite3.connect(result["backup"]) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 5)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertTrue(separate_pipelines(self.db, self.folder)["already_separate"])
        self.assertEqual(len(list((self.root / "backups").glob("*.db"))), 1)

    def test_archive_failure_keeps_active_data_and_allows_retry(self):
        self.add_jobs(source="reader_linkedin")
        original = sqlite3.connect
        def connect(path, *args, **kwargs):
            if str(path).endswith("previous_platform_imports.sqlite3"):
                raise OSError("Archive unavailable")
            return original(path, *args, **kwargs)
        with patch("backend.core.separate_pipelines.sqlite3.connect", side_effect=connect):
            with self.assertRaises(OSError): separate_pipelines(self.db, self.folder)
        self.assertEqual(len(self.rows()), 1)
        self.assertFalse(self.rows("SELECT * FROM platform_settings"))

    @unittest.skipUnless(READER_ROOT.is_dir(), "Requires sibling reader")
    def test_reader_collection_writes_only_its_json_store(self):
        self.add_jobs()
        self.service.start()
        self.addCleanup(self.service.close)
        dashboard, _, _ = reader_modules()
        def execute(args):
            value = {"status": "completed", "jobs": [{"job_id": "123", "title": "Reader fixture", "company": "Fixture", "description": "SQL", "link": "https://www.linkedin.com/jobs/view/123/"}], "errors": [], "search_url": args.url}
            args.output.write_text(json.dumps(value), encoding="utf-8")
            return value, 0
        self.service.reader = dashboard.Manager(self.folder, execute=execute, bootstrap=lambda: None)
        response = self.client.post("/api/platform/reader/start", json={"url": "https://www.linkedin.com/jobs/search/?keywords=python", "limit": 1}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.service.reader.thread.join(timeout=3)
        self.assertEqual(self.client.get("/api/platform/reader/state").json()["saved"], 1)
        self.assertEqual(len(self.rows()), 1)
        self.assertFalse(self.rows("SELECT * FROM job_origins"))

    @unittest.skipUnless(READER_ROOT.is_dir(), "Requires sibling reader")
    def test_reader_download_keeps_checkpoint_and_blocks_path_traversal(self):
        value = {"jobs": [], "errors": [], "status": "completed"}
        (self.folder / "run.json").write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual(self.client.get("/api/platform/reader/download?file=run.json").json(), value)
        self.assertEqual(self.client.get("/api/platform/reader/download?file=../outside.json").status_code, 404)

    def test_offline_blocks_collection_but_allows_json_export(self):
        ids = self.add_jobs()
        with patch.dict("os.environ", {"JOB_INTEL_OFFLINE": "1"}):
            self.assertEqual(self.client.post("/api/platform/careers/start", json={}, headers=self.headers).status_code, 400)
            self.assertEqual(self.export(ids).status_code, 200)

    def test_career_process_logs_duplicate_start_and_stop_without_network(self):
        original = subprocess.Popen
        def fixture_process(*args, **kwargs):
            return original([sys.executable, "-u", "-c", "import time; print('fixture collection started',flush=True); time.sleep(20)"], **kwargs)
        with patch("backend.core.pipelines.subprocess.Popen", side_effect=fixture_process):
            self.service.start_careers()
            self.addCleanup(self.service.close)
            deadline = time.monotonic() + 5
            while not self.service.logs and time.monotonic() < deadline: time.sleep(0.02)
            self.assertIn("fixture collection started", self.service.snapshot()["career"]["logs"])
            with self.assertRaises(RuntimeError): self.service.start_careers()
            self.service.stop_careers()
            self.service.career_thread.join(timeout=5)
            self.assertEqual(self.service.snapshot()["career"]["status"], "stopped")


if __name__ == "__main__": unittest.main()
