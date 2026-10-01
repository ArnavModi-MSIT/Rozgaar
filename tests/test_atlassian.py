import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from core.storage import init_db, refresh_atlassian_job
from fetchers import atlassian


class AtlassianTests(unittest.TestCase):
    def test_job_links_to_official_details_page(self):
        job = atlassian._parse_job({
            "id": 26328, "title": "Solutions Architect | DX",
            "locations": ["Salt Lake City, United States", "Remote - Remote"],
            "applyUrl": "https://careers-americas.icims.com/jobs/26328/job?mode=apply",
            "overview": "<p>Role details</p>",
        })
        self.assertEqual(job["url"], "https://www.atlassian.com/company/careers/details/26328")
        self.assertIn("United States", job["location"])
        self.assertEqual(job["description"], "Role details")

    @patch("fetchers.atlassian._get", return_value=None)
    def test_failed_listing_is_not_an_empty_success(self, _get):
        with self.assertRaisesRegex(RuntimeError, "unavailable listings"):
            atlassian.fetch_all()

    @patch("fetchers.atlassian._get", return_value=[])
    def test_valid_empty_listing(self, _get):
        self.assertEqual(atlassian.fetch_all(), [])

    def test_saved_row_refresh_preserves_dismissal_and_api_link(self):
        from api import data

        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "jobs.db")
            with closing(sqlite3.connect(db_path)) as conn:
                init_db(conn)
                conn.execute(
                    "INSERT INTO jobs (id,company,title,location,url,description,source,first_seen,dismissed) VALUES (?,?,?,?,?,?,?,?,?)",
                    ("atlassian:26328", "atlassian", "Solutions Architect | DX", "",
                     "https://careers-americas.icims.com/jobs/26328/job?mode=apply", "Old text", "atlassian", 1, 0),
                )
                conn.commit()
            with patch.object(data, "DB_PATH", db_path):
                visible = data._load_jobs_df()
            self.assertEqual(visible.iloc[0]["url"], "https://www.atlassian.com/company/careers/details/26328")
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("UPDATE jobs SET dismissed = 1 WHERE id = 'atlassian:26328'")
                job = {"title": "Solutions Architect | DX", "location": "Salt Lake City, United States",
                       "url": "https://www.atlassian.com/company/careers/details/26328", "description": "Current text"}
                self.assertTrue(refresh_atlassian_job(conn, "atlassian:26328", job))
                self.assertFalse(refresh_atlassian_job(conn, "atlassian:26328", job))
                saved = conn.execute("SELECT location,url,description,dismissed FROM jobs WHERE id = 'atlassian:26328'").fetchone()
                self.assertEqual(saved, (job["location"], job["url"], job["description"], 1))


if __name__ == "__main__":
    unittest.main()
