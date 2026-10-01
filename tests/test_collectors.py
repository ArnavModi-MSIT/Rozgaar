"""Offline collector contract tests using small, non-sensitive response fixtures."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fetchers import standard, unstop


FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class UnstopTests(unittest.TestCase):
    def test_collect_fetches_jobs_only(self):
        with patch.object(unstop, "_get", return_value=fixture("unstop_jobs.json")["data"]) as get:
            result = unstop.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["location"], "Delhi, India")
        self.assertIn("Experience required: 1 years.", result[0]["description"])
        get.assert_called_once_with("jobs", 1)

    def test_later_page_failure_is_partial(self):
        first = fixture("unstop_jobs.json")["data"]
        first["total"] = 60
        with patch.object(unstop, "_get", side_effect=[first, None]), patch.object(unstop.time, "sleep"):
            result = unstop._fetch_type("jobs")
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("page 2 request failed", result.error)

    def test_first_page_failure_is_not_an_empty_success(self):
        with patch.object(unstop, "_get", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "page 1 request failed"):
                unstop._fetch_type("jobs")

    def test_collect_fails_when_jobs_request_fails(self):
        with patch.object(unstop, "_get", return_value=None) as get:
            with self.assertRaisesRegex(RuntimeError, "jobs: page 1 request failed"):
                unstop.collect()
        get.assert_called_once_with("jobs", 1)


class GreenhouseTests(unittest.TestCase):
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
