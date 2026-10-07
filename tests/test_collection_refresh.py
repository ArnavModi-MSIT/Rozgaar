"""Regressions for complete source text and responsive collection writes."""

from contextlib import nullcontext
import sqlite3
import unittest
from unittest.mock import patch

import run
from core.experience import extract_min_experience
from core.storage import init_db, save_job
from fetchers import standard


class CompleteStandardDescriptionsTests(unittest.TestCase):
    def test_lever_retains_late_qualification_section(self):
        posting = {
            "id": "lever-1", "text": "Data Analyst",
            "hostedUrl": "https://jobs.lever.co/example/lever-1",
            "descriptionPlain": "Company background " * 500,
            "lists": [{"text": "Requirements", "content": "<ul><li>3 years of experience in SQL.</li></ul>"}],
            "categories": {"location": "Delhi, India"},
        }
        with patch.object(standard, "_get", return_value=[posting]):
            job = standard.fetch_lever("example")[0]
        self.assertGreater(len(job["description"]), 6000)
        self.assertEqual(extract_min_experience(job["description"]), 3)

    def test_ashby_retains_late_qualification_section(self):
        posting = {
            "id": "ashby-1", "title": "Data Analyst",
            "jobUrl": "https://jobs.ashbyhq.com/example/ashby-1",
            "descriptionPlain": "Company background " * 500 + "\nRequirements\n4 years of experience in analytics.",
            "location": "Delhi, India",
        }
        with patch.object(standard, "_get", return_value={"jobs": [posting]}):
            job = standard.fetch_ashby("example")[0]
        self.assertGreater(len(job["description"]), 6000)
        self.assertEqual(extract_min_experience(job["description"]), 4)


class _ImmediateFuture:
    def __init__(self, fn, args):
        self.fn, self.args = fn, args

    def result(self):
        return self.fn(*self.args)


class _ImmediatePool:
    """Control network completion without threads or live requests."""
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, fn, *args):
        return _ImmediateFuture(fn, args)


class CollectionTransactionTests(unittest.TestCase):
    def run_fixture(self, platforms, conn):
        with patch.object(run, "collection_lock", return_value=nullcontext()), \
             patch.object(run, "PLATFORMS", platforms), \
             patch.object(run, "ThreadPoolExecutor", _ImmediatePool), \
             patch.object(run.sqlite3, "connect", return_value=conn), \
             patch.object(run, "process_backlog"), \
             patch.object(run, "cleanup_old", return_value=0), \
             patch.dict(run.os.environ, {"JOB_INTEL_OFFLINE": "0"}):
            run.run()

    def test_each_source_commits_before_waiting_for_next_source(self):
        conn = sqlite3.connect(":memory:")
        transaction_states = []
        job = {"company": "example", "source_id": "1", "title": "Data Analyst",
               "location": "Delhi, India", "url": "https://example.com/1",
               "description": "SQL analytics"}

        def second_source(deadline):
            transaction_states.append(conn.in_transaction)
            return []

        def failed_source(deadline):
            raise RuntimeError("fixture source failure")

        self.run_fixture([
            ("first", lambda deadline: [job]),
            ("second", second_source),
            ("failed", failed_source),
            ("after_failure", second_source),
        ], conn)
        self.assertEqual(transaction_states, [False, False])

    def test_existing_deloitte_description_is_refreshed(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        job = {"company": "deloitte", "source_id": "60362244", "title": "Senior Executive Analytics",
               "location": "Mumbai, India", "url": "https://example.com/60362244",
               "description": "old short summary"}
        save_job(conn, "deloitte:60362244", job, "deloitte")
        conn.execute("UPDATE jobs SET dismissed = 1, skills = 'sql', category = 'Data Analyst', experience_years = -1")
        conn.commit()
        new_job = dict(job, description="Requirements\n4-7 years of experience in FRM.")
        captured = []

        def inspect_saved(deadline):
            captured.append(conn.execute(
                "SELECT description, skills, category, experience_years, dismissed FROM jobs"
            ).fetchone())
            return []

        self.run_fixture([
            ("deloitte", lambda deadline: [new_job]),
            ("inspect", inspect_saved),
        ], conn)
        self.assertEqual(captured, [(new_job["description"], None, None, None, 1)])


if __name__ == "__main__":
    unittest.main()
