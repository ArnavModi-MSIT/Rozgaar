import argparse
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import url_reader.dashboard as dashboard
import url_reader.sources.instahyre as instahyre
import url_reader.engine as reader
from url_reader.identity import canonical_job_url, posting_key, source_for_url
from url_reader.storage.history import SeenPostings

JOB = "https://www.instahyre.com/job-12345-analyst-at-fixture-delhi/"


class InstahyreTests(unittest.TestCase):
    def test_search_preserves_zero_and_resets_only_cursor(self):
        normalized = reader.search_url(instahyre.DEFAULT_SEARCH + "&page=2")
        self.assertIn("years=0", normalized)
        self.assertIn("job_type=0", normalized)
        self.assertNotIn("page=", normalized)
        self.assertEqual(reader.search_signature(normalized), reader.search_signature(instahyre.DEFAULT_SEARCH))
        self.assertEqual(reader.search_signature("https://instahyre.com/candidate/opportunities/?search=true"),
                         reader.search_signature("https://www.instahyre.com/candidate/opportunities/?company_size=0&job_type=0&search=true"))

    def test_filters_change_search_identity(self):
        for query in ("&skills=Python", "&location=Delhi"):
            self.assertNotEqual(reader.search_signature(instahyre.DEFAULT_SEARCH),
                                reader.search_signature(instahyre.DEFAULT_SEARCH + query))

    def test_rejects_wrong_routes_feeds_and_filter_values(self):
        for value in (JOB, "http://www.instahyre.com/candidate/opportunities/", "https://user:pass@www.instahyre.com/candidate/opportunities/",
                      "https://www.instahyre.com:444/candidate/opportunities/", "https://www.instahyre.com.evil/candidate/opportunities/",
                      "https://www.instahyre.com/candidate/opportunities/?matching=true",
                      instahyre.DEFAULT_SEARCH + "&years=3", instahyre.DEFAULT_SEARCH.replace("years=0", "years=-1"),
                      instahyre.DEFAULT_SEARCH.replace("years=0", "years=26"),
                      instahyre.DEFAULT_SEARCH.replace("job_type=0", "job_type=99")):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                reader.search_url(value)

    def test_identity_is_stable_across_slug_redirects(self):
        self.assertEqual(posting_key(JOB), ("instahyre", "12345"))
        self.assertEqual(posting_key(JOB), posting_key("https://www.instahyre.com/job-12345/"))
        self.assertEqual(canonical_job_url(JOB + "?source=test#section"), JOB)
        self.assertEqual(source_for_url(JOB), "instahyre")
        for value in (JOB.replace("https:", "http:"), JOB.replace("www.", "user:pass@www."),
                      JOB.replace(".com/", ".com:444/"), "https://www.instahyre.com/job-abc/", "https://www.instahyre.com/job-12345/a/"):
            self.assertIsNone(posting_key(value))

    def test_history_deduplicates_other_days_and_aliases(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            path = Path(folder)/"history.sqlite3"
            with SeenPostings(path) as history:
                history.remember({"link": JOB, "title": "Analyst", "company": "Fixture", "description": "Complete duties."}, "yesterday.json")
            with SeenPostings(path) as history:
                self.assertTrue(history.was_seen("https://www.instahyre.com/job-12345/"))
                self.assertFalse(history.was_seen("https://www.linkedin.com/jobs/view/12345/"))

    def test_all_reader_operations_route_to_instahyre(self):
        page = Mock(url=instahyre.DEFAULT_SEARCH)
        for method, args in (("job_links", (page,)), ("collect_links", (page, 10)), ("next_results", (page,))):
            with patch.object(instahyre, method, return_value="routed"):
                self.assertEqual(getattr(reader, method)(*args), "routed")
        with patch.object(instahyre, "read_job", return_value="routed"):
            self.assertEqual(reader.read_job(page, JOB), "routed")
        with patch.object(instahyre, "navigate_search") as navigate, patch.object(reader, "navigate_page") as raw:
            reader.navigate(page, instahyre.DEFAULT_SEARCH)
            navigate.assert_called_once_with(page, instahyre.DEFAULT_SEARCH)
            raw.assert_not_called()

    def test_other_tabs_never_supply_job_links(self):
        page = Mock(url=instahyre.DEFAULT_SEARCH)
        page.locator.return_value.all_inner_texts.return_value = ["Recommended jobs\n10"]
        self.assertEqual(instahyre.job_links(page), [])
        page.locator.return_value.evaluate_all.assert_not_called()
        with patch.object(reader, "check_access"), self.assertRaisesRegex(ValueError, "Search Results"):
            instahyre.collect_links(page, 10)

    def test_cancelled_discovery_does_not_touch_browser(self):
        event = threading.Event()
        event.set()
        page = Mock()
        with self.assertRaises(KeyboardInterrupt):
            instahyre.collect_links(page, 10, event)
        page.locator.assert_not_called()

    def test_login_stops_with_source_specific_message(self):
        page = Mock(url="https://www.instahyre.com/login/?next=/candidate/opportunities/")
        page.is_closed.return_value = False
        with self.assertRaisesRegex(reader.AccessBlocked, "Instahyre"):
            reader.check_access(page)

    def test_checkpoint_source_and_filename(self):
        self.assertTrue(reader.daily_output_path(instahyre.DEFAULT_SEARCH).name.startswith("instahyre_"))
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            args = SimpleNamespace(output=Path(folder)/"backend.collector.json", fresh=False, limit=10)
            result = {"jobs": [], "errors": []}
            reader.prepare_output(args, result, reader.search_url(instahyre.DEFAULT_SEARCH))
            self.assertEqual(result["source"], "instahyre")
            reader.validate_checkpoint(result, instahyre.DEFAULT_SEARCH)

    def test_dashboard_accepts_search_and_three_workers(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            stop = threading.Event()
            def execute(args):
                stop.wait(2)
                return {"status": "interrupted"}, 130
            manager = dashboard.Manager(folder, execute=execute, bootstrap=lambda: None)
            try:
                manager.start({"url": instahyre.DEFAULT_SEARCH, "limit": 10, "delay": 1, "workers": 3})
                self.assertEqual(manager.args.workers, 3)
                self.assertEqual(dashboard.source_name(manager.args.url), "instahyre")
                self.assertTrue(manager.args.output.name.startswith("instahyre_"))
            finally:
                stop.set()
                manager.thread.join(3)


if __name__ == "__main__":
    unittest.main()
