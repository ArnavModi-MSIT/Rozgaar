import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from core.location import is_india_or_unknown, parse_country
from core.storage import init_db


class LocationFilterTests(unittest.TestCase):
    def test_known_us_locations_are_rejected(self):
        for location in (
            "San Francisco, California", "Mountain View, California",
            "Remote - California", "Seattle, Washington", "San Francisco",
            "New York City", "Washington, D.C.",
        ):
            with self.subTest(location=location):
                self.assertEqual(parse_country(location), "United States")
                self.assertFalse(is_india_or_unknown(location))

    def test_india_and_unknown_remain_available(self):
        for location in ("Bengaluru, India", "India - Remote", "IN-Pune"):
            self.assertEqual(parse_country(location), "India")
        self.assertTrue(is_india_or_unknown("Location to be confirmed"))

    def test_api_hides_existing_foreign_unstop_and_removed_internship_rows(self):
        from api import data

        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "jobs.db")
            with closing(sqlite3.connect(db_path)) as conn:
                init_db(conn)
                conn.executemany(
                    "INSERT INTO jobs (id, company, title, location, url, description, source, first_seen, dismissed) VALUES (?, 'test', 'Analyst', ?, ?, '', ?, 1, 0)",
                    [
                        ("india", "Bengaluru, India", "https://example.com", "test"),
                        ("us", "San Francisco, California", "https://example.com", "test"),
                        ("unknown", "Location to be confirmed", "https://example.com", "test"),
                        ("unstop-job", "Delhi, India", "https://unstop.com/jobs/analyst-1", "unstop"),
                        ("unstop-internship", "Delhi, India", "https://unstop.com/internships/analyst-2", "unstop"),
                        ("linkedin-job", "Delhi, India", "https://linkedin.com/jobs/view/1", "linkedin"),
                        ("internshala-job", "Delhi, India", "https://internshala.com/job/detail/analyst-1", "internshala"),
                        ("internshala-internship", "Delhi, India", "https://internshala.com/internship/detail/analyst-2", "internshala"),
                    ],
                )
                conn.commit()
            with patch.object(data, "DB_PATH", db_path):
                visible = data._load_jobs_df()
            self.assertEqual(set(visible["id"]), {"india", "unknown"})
            with closing(sqlite3.connect(db_path)) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM jobs").fetchone()[0], 8)


if __name__ == "__main__":
    unittest.main()
