import argparse
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import url_reader.dashboard as dashboard
import url_reader.engine as reader
import url_reader.sources.wellfound as wellfound
from url_reader.identity import canonical_job_url, posting_key, source_for_url
from url_reader.storage.history import SeenPostings
from url_reader.browser.pagination import PaginationResult

JOB = "https://wellfound.com/jobs/12345-data-analyst"


class WellfoundTests(unittest.TestCase):
    def test_curated_end_is_informational_and_does_not_advance(self):
        page = Mock(url=wellfound.DEFAULT_SEARCH)
        page.get_by_role.return_value.all.return_value = [Mock(is_visible=lambda: True)]
        page.locator.return_value.all_inner_texts.return_value = []
        with patch.object(wellfound, "job_links", return_value=[JOB]), patch.object(reader, "interruptible_wait"), patch.object(reader, "check_access"), patch("url_reader.browser.pagination.advance", return_value=PaginationResult("missing_control", page.url, 1)):
            result = wellfound.next_results(page)
        self.assertFalse(result)
        self.assertEqual(result.status, "curated_list_end")
        self.assertEqual(result.error, "")
        self.assertIn("highlights list", result.reason)
        self.assertIn("India", result.reason)

    def test_unknown_jobs_layout_is_not_assumed_to_be_curated(self):
        page = Mock(url=wellfound.DEFAULT_SEARCH)
        page.get_by_role.return_value.all.return_value = []
        page.locator.return_value.all_inner_texts.return_value = []
        with patch.object(wellfound, "job_links", return_value=[JOB]), patch.object(reader, "interruptible_wait"), patch.object(reader, "check_access"), patch("url_reader.browser.pagination.advance", return_value=PaginationResult("missing_control", page.url, 1)):
            self.assertEqual(wellfound.next_results(page).status, "missing_control")

    def test_supported_search_routes(self):
        for path in ("/jobs", "/location/india", "/role/data-analyst", "/role/l/data-analyst/india", "/company/fixture/jobs"):
            with self.subTest(path=path):
                self.assertEqual(reader.search_url("https://www.wellfound.com" + path + "/?page=2"), "https://wellfound.com" + path)

    def test_filters_preserved_pagination_ignored(self):
        url = "https://wellfound.com/location/india?remote=true&roles[]=data&roles[]=engineering&empty=&page=3"
        normalized = reader.search_url(url)
        self.assertIn("roles%5B%5D=data&roles%5B%5D=engineering&empty=", normalized)
        self.assertEqual(reader.search_signature(url), reader.search_signature(normalized))
        self.assertNotEqual(reader.search_signature(url), reader.search_signature(url.replace("remote=true", "remote=false")))

    def test_rejects_unsafe_or_unrelated_search(self):
        for value in (JOB, "http://wellfound.com/jobs", "https://wellfound.com.evil/jobs", "https://user:pass@wellfound.com/jobs", "https://wellfound.com:444/jobs", "https://wellfound.com/login", "https://wellfound.com/jobs/12345/extra", "https://wellfound.com:bad/jobs"):
            with self.subTest(value=value), self.assertRaises((argparse.ArgumentTypeError, ValueError)):
                reader.search_url(value)

    def test_stable_identity_and_canonical_links(self):
        self.assertEqual(posting_key(JOB), ("wellfound", "12345"))
        self.assertEqual(posting_key(JOB), posting_key("https://www.wellfound.com/jobs/12345-new-slug/"))
        self.assertEqual(canonical_job_url(JOB + "/?utm_source=test#description"), JOB)
        self.assertEqual(source_for_url(JOB), "wellfound")
        for value in (JOB.replace("https:", "http:"), JOB.replace(".com/", ".com:444/"), JOB.replace("wellfound.com", "user@wellfound.com"), JOB + "/extra", "https://wellfound.com/jobs/abc"):
            self.assertIsNone(posting_key(value))

    def test_source_scoped_seen_history(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder, SeenPostings(Path(folder)/"seen.sqlite3") as history:
            history.remember({"link": JOB, "title": "Analyst", "company": "Fixture", "description": "Full description."}, "backend.collector.json")
            self.assertTrue(history.was_seen("https://wellfound.com/jobs/12345"))
            self.assertFalse(history.was_seen("https://www.linkedin.com/jobs/view/12345/"))

    def test_reader_routes_all_operations(self):
        page = Mock(url=wellfound.DEFAULT_SEARCH)
        for method, args in (("job_links", (page,)), ("collect_links", (page, 10)), ("next_results", (page,)), ("read_job", (page, JOB))):
            with patch.object(wellfound, method, return_value="routed"):
                self.assertEqual(getattr(reader, method)(*args), "routed")

    def test_cancel_does_not_touch_browser(self):
        event = threading.Event()
        event.set()
        page = Mock()
        with self.assertRaises(KeyboardInterrupt):
            wellfound.collect_links(page, 10, event)
        page.locator.assert_not_called()

    def test_login_and_verification_stop(self):
        for url, title in (("https://wellfound.com/login", "Login"), (wellfound.DEFAULT_SEARCH, "Just a moment..."), (wellfound.DEFAULT_SEARCH, "Access denied")):
            page = Mock(url=url)
            page.is_closed.return_value = False
            page.title.return_value = title
            with self.assertRaisesRegex(reader.AccessBlocked, "Wellfound"):
                reader.check_access(page)

    def test_jsonld_matches_identity_in_graph(self):
        wanted = {"@type": ["JobPosting"], "identifier": {"value": "12345"}, "title": "Right"}
        unrelated = {"@type": "JobPosting", "identifier": {"value": "99999"}, "title": "Wrong"}
        self.assertEqual(wellfound.jobposting_data(["broken", json.dumps({"@graph": [unrelated, wanted]})], JOB), wanted)
        self.assertEqual(wellfound.jobposting_data([json.dumps(unrelated)], JOB), {})

    def test_jsonld_url_and_unidentified_single_posting(self):
        wanted = {"@type": "JobPosting", "url": JOB + "?ref=test"}
        self.assertEqual(wellfound.jobposting_data([json.dumps(wanted)], JOB), wanted)
        wanted = {"@type": "JobPosting", "description": "Only posting on page"}
        self.assertEqual(wellfound.jobposting_data([json.dumps([wanted])], JOB), wanted)

    def test_description_retains_full_text_and_paragraphs(self):
        text = "Full requirement " * 1500
        self.assertEqual(wellfound.description_text("<p>SQL &amp; Python</p><ul><li>" + text + "</li></ul><script>unrelated()</script>"), "SQL & Python\n" + text.strip())

    def test_salary_and_multiple_locations(self):
        self.assertEqual(wellfound.salary_text({"currency": "INR", "value": {"minValue": 400000, "maxValue": 600000, "unitText": "YEAR"}}), "INR 400000 – 600000 YEAR")
        self.assertEqual(wellfound.location_text({"jobLocationType": "TELECOMMUTE", "jobLocation": [{"address": {"addressLocality": "Delhi", "addressCountry": {"name": "India"}}}]}), "Remote; Delhi, India")

    def test_checkpoint_and_filename(self):
        self.assertTrue(reader.daily_output_path(wellfound.DEFAULT_SEARCH).name.startswith("wellfound_"))
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            result = {"jobs": [], "errors": []}
            reader.prepare_output(SimpleNamespace(output=Path(folder)/"backend.collector.json", fresh=False, limit=10), result, wellfound.DEFAULT_SEARCH)
            self.assertEqual(result["source"], "wellfound")
            reader.validate_checkpoint(result, wellfound.DEFAULT_SEARCH)

    def test_dashboard_accepts_wellfound_three_workers(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            stop = threading.Event()
            def execute(args):
                stop.wait(2)
                return {"status": "interrupted"}, 130
            manager = dashboard.Manager(folder, execute=execute, bootstrap=lambda: None)
            try:
                manager.start({"url": wellfound.DEFAULT_SEARCH, "limit": 10, "delay": 1, "workers": 3})
                self.assertEqual(manager.args.workers, 3)
                self.assertEqual(dashboard.source_name(manager.args.url), "wellfound")
            finally:
                stop.set()
                manager.thread.join(3)


if __name__ == "__main__":
    unittest.main()
