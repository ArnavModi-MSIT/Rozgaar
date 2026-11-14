import os
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from backend.core.source_health import record_company_run
from backend.core.storage import init_db, load_known_job_locations
from backend.fetchers import workday_india
from backend.fetchers.result import CollectionResult

CFG = {"company": "cigna", "tenant": "cigna", "wd_server": "wd5", "site": "cignacareers", "verify_detail_country": True}
FACETS = {"jobPostings": [], "facets": [{"facetParameter": "Location_Country", "values": [{"id": "in", "descriptor": "India"}]}]}


def row(i):
    return {"title": f"Analyst {i}", "externalPath": f"/job/India/{i}", "bulletFields": [str(i)], "locationsText": "Hyderabad"}


class KnownJobTests(unittest.TestCase):
    def test_saved_job_skips_detail_fetch_and_keeps_stored_location(self):
        pages = [FACETS, {"total": 1, "jobPostings": [row(1)]}]
        with patch.object(workday_india, "post_json", side_effect=pages), \
             patch.object(workday_india, "get_json") as detail, patch.object(workday_india.time, "sleep"):
            result = workday_india.fetch(CFG, known={"cigna:1": "Hyderabad, India"})
        detail.assert_not_called()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["location"], "Hyderabad, India")
        self.assertEqual(result[0]["description"], "")
        self.assertTrue(result[0]["_description_known"])

    def test_new_job_is_still_fetched_and_checked(self):
        pages = [FACETS, {"total": 2, "jobPostings": [row(1), row(2)]}]
        info = {"jobPostingInfo": {"country": {"descriptor": "India"}, "location": "Hyderabad", "jobDescription": "<p>SQL</p>"}}
        with patch.object(workday_india, "post_json", side_effect=pages), \
             patch.object(workday_india, "get_json", return_value=info) as detail, patch.object(workday_india.time, "sleep"):
            result = workday_india.fetch(CFG, known={"cigna:1": "Hyderabad, India"})
        self.assertEqual(detail.call_count, 1)
        by_id = {job["source_id"]: job for job in result}
        self.assertEqual(by_id["2"]["description"], "SQL")
        self.assertNotIn("_description_known", by_id["2"])

    def test_known_job_is_not_counted_as_missing_description(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        job = {"company": "cigna", "location": "Hyderabad, India", "description": "", "_description_known": True}
        record_company_run(conn, 1, "workday_india", [job])
        self.assertEqual(conn.execute("SELECT missing_descriptions FROM company_runs WHERE company='cigna'").fetchone()[0], 0)

    def test_loader_returns_only_saved_jobs_with_descriptions(self):
        path = os.path.join(tempfile.mkdtemp(), "jobs.db")
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE jobs (id TEXT, source TEXT, location TEXT, description TEXT)")
        conn.executemany("INSERT INTO jobs VALUES (?,?,?,?)", [
            ("cigna:1", "workday_india", "Hyderabad, India", "text"),
            ("cigna:2", "workday_india", "Pune, India", ""),
            ("x:3", "workday", "Noida, India", "text"),
        ])
        conn.commit()
        conn.close()
        self.assertEqual(load_known_job_locations(path, "workday_india"), {"cigna:1": "Hyderabad, India"})
        self.assertEqual(load_known_job_locations(os.path.join(tempfile.mkdtemp(), "missing.db"), "workday_india"), {})


class SplitCollectTests(unittest.TestCase):
    def test_late_boards_run_while_early_boards_are_still_busy(self):
        configs = [{"company": f"c{i}"} for i in range(10)]
        tail_done, release = [], threading.Event()

        def fake_fetch(cfg, deadline=None, known=None):
            index = int(cfg["company"][1:])
            if index < 5:
                # Early boards stay busy until every late board has finished.
                self.assertTrue(release.wait(10), "late boards never started")
            else:
                tail_done.append(index)
                if len(tail_done) == 5:
                    release.set()
            return CollectionResult([{"company": cfg["company"], "source_id": "1"}], status="ok")

        with patch.object(workday_india, "fetch", side_effect=fake_fetch):
            result = workday_india.collect(configs)
        self.assertEqual([job["company"] for job in result], [f"c{i}" for i in range(10)])
        self.assertEqual(result.status, "ok")

    def test_small_list_and_known_are_passed_through(self):
        seen = []
        with patch.object(workday_india, "fetch", side_effect=lambda cfg, deadline=None, known=None: seen.append(known) or CollectionResult([], status="ok")):
            workday_india.collect([{"company": "a"}, {"company": "b"}], known={"a:1": "x"})
        self.assertEqual(seen, [{"a:1": "x"}, {"a:1": "x"}])


if __name__ == "__main__":
    unittest.main()
