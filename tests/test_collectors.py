"""Offline collector contract tests using small, non-sensitive response fixtures."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from core.collector import PLATFORMS
from fetchers import standard


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class RegistryTests(unittest.TestCase):
    def test_unstop_is_not_collected(self):
        for source in ("unstop", "linkedin", "internshala"):
            self.assertNotIn(source, [name for name, _ in PLATFORMS])


class GreenhouseTests(unittest.TestCase):
    def test_escaped_html_and_late_experience_are_retained(self):
        import html
        from core.experience import extract_min_experience
        body = "<p>" + "Company background "*700 + "</p><h3>About you:</h3><li>3–5 years of experience in data analysis.</li>"
        response = {"jobs":[{"id":1,"title":"AI Data Analyst","location":{"name":"India"},"absolute_url":"https://example.com","content":html.escape(body)}]}
        with patch.object(standard,"_get",return_value=response):
            job=standard.fetch_greenhouse("example")[0]
        self.assertGreater(len(job["description"]),6000)
        self.assertNotIn("<li",job["description"])
        self.assertEqual(extract_min_experience(job["description"]),3)

    def test_saved_description_refresh_preserves_user_state(self):
        import sqlite3
        from core.storage import refresh_collected_description
        conn=sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE jobs(id TEXT, description TEXT, category TEXT, skills TEXT, experience_years INTEGER, dismissed INTEGER, first_seen INTEGER)")
        conn.execute("INSERT INTO jobs VALUES('a','old','data','sql',NULL,1,123)")
        self.assertTrue(refresh_collected_description(conn,'a',{'description':'3 years of experience'}))
        self.assertFalse(refresh_collected_description(conn,'a',{'description':''}))
        self.assertEqual(conn.execute("SELECT dismissed,first_seen,skills,description FROM jobs").fetchone(),(1,123,None,'3 years of experience'))
        conn.close()

    def test_normalizes_html_and_identity(self):
        with patch.object(standard, "_get", return_value=fixture("greenhouse.json")):
            jobs = standard.fetch_greenhouse("example")
        self.assertEqual(jobs[0]["source_id"], "303")
        self.assertEqual(jobs[0]["location"], "Gurugram, India")
        self.assertIn("SQL", jobs[0]["description"])
        self.assertNotIn("<li>", jobs[0]["description"])

    def test_empty_board_and_failed_board_are_different(self):
        with patch.object(standard, "_get", return_value={"jobs": []}):
            self.assertEqual(standard.fetch_greenhouse("empty"), [])
        with patch.object(standard, "_get", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "missing jobs list"):
                standard.fetch_greenhouse("broken")

    def test_one_failed_board_marks_platform_partial(self):
        def fetch(slug):
            if slug == "broken":
                raise RuntimeError("fixture failure")
            return [{"source_id": "1"}]

        with patch.object(standard, "fetch_greenhouse", side_effect=fetch):
            with self.assertLogs("jobbot", level="ERROR"):
                result = standard.collect(["working", "broken"], [], [])
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("greenhouse:broken", result.error)


if __name__ == "__main__":
    unittest.main()


class RubrikLocationTests(unittest.TestCase):
    def test_india_office_normalizes_city_only_location(self):
        job = {"location": {"name": "Bangalore"}, "offices": [{"name": "Bangalore, India Office"}]}
        self.assertEqual(standard._greenhouse_location("rubrik", job), "Bangalore, India")
        self.assertEqual(standard._greenhouse_location("other", job), "Bangalore")

    def test_foreign_office_stays_foreign(self):
        job = {"location": {"name": "Palo Alto, CA"}, "offices": [{"name": "Palo Alto, CA HQ Office"}]}
        self.assertEqual(standard._greenhouse_location("rubrik", job), "Palo Alto, CA")
