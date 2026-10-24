import argparse
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import url_reader.dashboard as dashboard
import url_reader.sources.naukri as naukri
import url_reader.engine as reader
from url_reader.identity import posting_key, canonical_job_url
from url_reader.storage.history import SeenPostings
from url_reader.browser.pagination import advance

JOB = "https://www.naukri.com/job-listings-analyst-intern-fixture-delhi-0-to-1-years-211026001234"


class NaukriTests(unittest.TestCase):
    def test_search_retains_user_internship_filters_and_resets_cursor(self):
        normalized = reader.search_url(naukri.DEFAULT_SEARCH)
        for item in ("k=analyst+internship", "experience=0", "naukriCampus=true", "qinternshipFlag=true", "qproductJobSource=2"):
            self.assertIn(item, normalized)
        self.assertEqual(reader.search_signature(normalized), reader.search_signature(normalized.replace("-jobs?", "-jobs-2?")))

    def test_invalid_search_urls_are_rejected(self):
        for url in (JOB, "https://www.naukri.com/mnjuser/homepage", "https://www.naukri.com.evil/analyst-jobs",
                    "https://user:password@www.naukri.com/analyst-jobs", "http://www.naukri.com/analyst-jobs"):
            with self.subTest(url=url), self.assertRaises(argparse.ArgumentTypeError):
                reader.search_url(url)

    def test_next_link_retains_filters_omitted_by_naukri(self):
        target = naukri.filtered_next_url(naukri.DEFAULT_SEARCH, "https://www.naukri.com/analyst-internship-jobs-2")
        self.assertIn("-jobs-2?", target)
        self.assertEqual(reader.search_signature(target), reader.search_signature(naukri.DEFAULT_SEARCH))
        with self.assertRaises(ValueError):
            naukri.filtered_next_url(naukri.DEFAULT_SEARCH, "https://www.naukri.com/developer-jobs-2")

    def test_identity_tracking_and_cross_site_separation(self):
        self.assertEqual(canonical_job_url(JOB + "?src=test"), JOB)
        self.assertEqual(posting_key(JOB), ("naukri", "211026001234"))
        self.assertIsNone(posting_key(JOB.replace("https:", "http:")))
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            with SeenPostings(Path(folder)/"history.sqlite3") as history:
                history.remember({"link": JOB, "title": "Analyst", "description": "Full duties."}, "old.json")
                self.assertTrue(history.was_seen(JOB + "?tracking=test"))
                self.assertFalse(history.was_seen("https://www.linkedin.com/jobs/view/211026001234/"))

    def test_location_pagination_preserves_repeated_salary_filters(self):
        current = "https://www.naukri.com/analyst-jobs-in-delhi-ncr?k=analyst&experience=0&ctcFilter=6to10&ctcFilter=10to15"
        second = naukri.filtered_next_url(current, "https://www.naukri.com/analyst-jobs-in-delhi-ncr-2")
        self.assertEqual(reader.search_signature(current), reader.search_signature(second))
        self.assertIn("ctcFilter=6to10&ctcFilter=10to15", second)
        third = naukri.filtered_next_url(second, "https://www.naukri.com/analyst-jobs-in-delhi-ncr-3")
        self.assertEqual(reader.search_signature(current), reader.search_signature(third))

    def test_all_operations_route_to_naukri_adapter(self):
        page = Mock(url=naukri.DEFAULT_SEARCH)
        for function, args in (("job_links", (page,)), ("collect_links", (page, 10)), ("next_results", (page,))):
            with patch.object(naukri, function, return_value="routed") as called:
                self.assertEqual(getattr(reader, function)(*args), "routed")
                called.assert_called_once()
        with patch.object(naukri, "read_job", return_value={"source": "naukri"}):
            self.assertEqual(reader.read_job(page, JOB)["source"], "naukri")

    def test_click_navigation_keeps_site_handler_and_checks_filters(self):
        for changed_filters in (False, True):
            with self.subTest(changed_filters=changed_filters):
                page = Mock(url=naukri.DEFAULT_SEARCH)
                control, group = Mock(), Mock()
                control.is_visible.return_value = control.is_enabled.return_value = True
                control.get_attribute.side_effect = lambda key: "/analyst-internship-jobs-2" if key == "href" else ""
                control.locator.return_value.count.return_value = 0
                control.inner_text.return_value = "Next"
                group.all.return_value = [control]
                target = naukri.filtered_next_url(page.url, "https://www.naukri.com/analyst-internship-jobs-2")
                control.click.side_effect = lambda **_: setattr(page, "url", target.split("?")[0] if changed_filters else target)
                links = Mock(side_effect=[[JOB], [JOB.replace("001234", "001235")]])
                with patch.object(reader, "navigate") as goto, patch.object(reader, "check_access"):
                    outcome = advance(page, [group], links, prefer_click=True,
                                      prepare_target=lambda _: target)
                goto.assert_not_called()
                control.click.assert_called_once()
                self.assertEqual(outcome.status, "navigation_failed" if changed_filters else "advanced")
                if changed_filters:
                    self.assertIn("changed the selected search filters", outcome.error)
                    self.assertEqual(outcome.current_page_url, page.url)

    def test_resume_replays_search_and_skips_saved_jobs(self):
        search = reader.search_url(naukri.DEFAULT_SEARCH)
        second = JOB.replace("001234", "001235")
        result = {"search_url": search, "jobs": [{"link": JOB}], "errors": [],
                  "progress": {"results_page_url": naukri.filtered_next_url(search, "https://www.naukri.com/analyst-internship-jobs-2"),
                               "pending_links": [], "attempted_links": [JOB], "page_complete": True}}
        page = Mock(url=search)
        worker = Mock()
        worker.read.return_value = {"link": second}
        with patch.object(reader, "navigate") as goto, patch.object(reader, "wait_for_content"), \
                patch.object(reader, "collect_links", side_effect=[[JOB], [second]]), \
                patch.object(reader, "next_results", return_value=True) as next_page, \
                patch.object(reader, "save_result"):
            reader.collect_jobs(page, worker, SimpleNamespace(limit=2, delay=1), result, Path("unused.json"))
        goto.assert_called_once_with(page, search)
        next_page.assert_called_once()
        worker.read.assert_called_once_with(second)
        self.assertEqual(result["status"], "completed")

    def test_checkpoint_naming_and_source(self):
        self.assertTrue(reader.daily_output_path(naukri.DEFAULT_SEARCH).name.startswith("naukri_"))
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            args = SimpleNamespace(output=Path(folder)/"jobs.json", fresh=False, limit=10)
            result = {"jobs": [], "errors": []}
            reader.prepare_output(args, result, reader.search_url(naukri.DEFAULT_SEARCH))
            self.assertEqual(result["source"], "naukri")
            reader.validate_checkpoint(result, naukri.DEFAULT_SEARCH)

    def test_verification_stops_naukri(self):
        page = Mock(url=naukri.DEFAULT_SEARCH)
        page.is_closed.return_value = False
        page.title.return_value = "Access Denied"
        with self.assertRaisesRegex(reader.AccessBlocked, "Naukri"):
            reader.check_access(page)

    def test_cancelled_discovery_makes_no_browser_calls(self):
        event = threading.Event()
        event.set()
        page = Mock(url=naukri.DEFAULT_SEARCH)
        with self.assertRaises(KeyboardInterrupt):
            naukri.collect_links(page, 10, event)
        page.locator.assert_not_called()

    def test_dashboard_accepts_naukri_and_three_readers(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            stop = threading.Event()
            def execute(args):
                stop.wait(2)
                return {"status": "interrupted", "stop_reason": "fixture"}, 130
            manager = dashboard.Manager(folder, execute=execute, bootstrap=lambda: None)
            try:
                manager.start({"url": naukri.DEFAULT_SEARCH, "limit": 10, "delay": 1, "workers": 3})
                self.assertEqual(manager.args.workers, 3)
                self.assertEqual(dashboard.source_name(manager.args.url), "naukri")
                self.assertTrue(manager.args.output.name.startswith("naukri_"))
            finally:
                stop.set()
                manager.thread.join(3)


if __name__ == "__main__":
    unittest.main()
