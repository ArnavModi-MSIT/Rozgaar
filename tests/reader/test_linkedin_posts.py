import argparse
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import url_reader.dashboard as dashboard
import url_reader.sources.linkedin_posts as linkedin_posts
import url_reader.engine as reader
from url_reader.identity import source_for_url, posting_key, canonical_job_url
from url_reader.storage.history import SeenPostings

POST = "https://www.linkedin.com/feed/update/urn:li:activity:12345/"
SLUG = "https://www.linkedin.com/posts/fixture_hiring-activity-12345-test/"


class LinkedInPostsTests(unittest.TestCase):
    def test_latest_sort_and_filters_are_preserved(self):
        normalized = reader.search_url(linkedin_posts.DEFAULT_SEARCH + "&datePosted=24h&page=2")
        self.assertIn("keywords=%23fresherhiring", normalized)
        self.assertIn("sortBy=%5B%22date_posted%22%5D", normalized)
        self.assertIn("datePosted=24h", normalized)
        self.assertNotIn("page=", normalized)
        self.assertNotIn("sortBy=DD", normalized)

    def test_posts_and_jobs_have_different_source_and_signature(self):
        self.assertEqual(source_for_url(linkedin_posts.DEFAULT_SEARCH), "linkedin_posts")
        self.assertEqual(source_for_url(POST), "linkedin_posts")
        self.assertEqual(source_for_url(reader.DEFAULT_SEARCH), "linkedin")
        self.assertNotEqual(reader.search_signature(linkedin_posts.DEFAULT_SEARCH), reader.search_signature(reader.DEFAULT_SEARCH))
        self.assertEqual(reader.search_signature(linkedin_posts.DEFAULT_SEARCH), reader.search_signature(linkedin_posts.DEFAULT_SEARCH.replace("origin=GLOBAL_SEARCH_HEADER", "origin=OTHER")))

    def test_strict_post_identity_and_canonical_urls(self):
        self.assertEqual(posting_key(POST), ("linkedin_posts", "activity:12345"))
        self.assertEqual(posting_key(POST), posting_key(SLUG + "?utm_source=share"))
        self.assertEqual(canonical_job_url(POST.replace("urn:li:", "urn%3Ali%3A") + "?tracking=x"), POST)
        self.assertEqual(canonical_job_url(SLUG + "?tracking=x"), SLUG)
        self.assertEqual(posting_key(SLUG.replace("activity-", "share-")), ("linkedin_posts", "share:12345"))
        self.assertNotEqual(posting_key(POST.replace("activity:", "ugcPost:")), posting_key(POST))
        for url in (POST.replace("https:", "http:"), POST.replace("www.", "user:pass@www."),
                    POST.replace(".com/", ".com:444/"), POST.replace(".com/", ".com.evil/"),
                    "https://www.linkedin.com/feed/update/urn:li:activity:abc/", "https://www.linkedin.com/posts/no-identifier/"):
            self.assertIsNone(posting_key(url))

    def test_unsupported_post_search_urls_are_rejected(self):
        for value in (POST, "https://www.linkedin.com/feed/", "http://www.linkedin.com/search/results/content/",
                      "https://www.linkedin.com:444/search/results/content/", "https://www.linkedin.com.evil/search/results/content/"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                reader.search_url(value)

    def test_history_deduplicates_posts_across_days_without_job_collisions(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            path = Path(folder)/"seen.sqlite3"
            with SeenPostings(path) as history:
                history.remember({"link": POST, "title": "Hiring", "description": "Full post text."}, "yesterday.json")
            with SeenPostings(path) as history:
                self.assertTrue(history.was_seen(SLUG))
                self.assertFalse(history.was_seen("https://www.linkedin.com/jobs/view/12345/"))

    def test_reader_operations_route_to_posts(self):
        page = Mock(url=linkedin_posts.DEFAULT_SEARCH)
        for name, args in (("job_links", (page,)), ("collect_links", (page, 10)), ("next_results", (page,))):
            with patch.object(linkedin_posts, name, return_value="routed"):
                self.assertEqual(getattr(reader, name)(*args), "routed")
        with patch.object(linkedin_posts, "read_job", return_value="routed"):
            self.assertEqual(reader.read_job(page, POST), "routed")

    def test_copied_short_link_resolves_only_official_post_redirects(self):
        page = Mock()
        response = page.context.request.get.return_value
        response.status, response.headers = 301, {"location": SLUG + "?utm_source=share"}
        self.assertEqual(linkedin_posts.resolve_copied_link(page, "https://lnkd.in/p/test"), SLUG)
        response.dispose.assert_called_once()
        response.headers = {"location": "https://evil.example/post"}
        with self.assertRaises(ValueError):
            linkedin_posts.resolve_copied_link(page, "https://lnkd.in/p/test")
        response.status = 429
        with self.assertRaises(reader.AccessBlocked):
            linkedin_posts.resolve_copied_link(page, "https://lnkd.in/p/test")

    def test_external_or_credential_links_are_never_resolved(self):
        page = Mock()
        for link in ("https://example.com/post", "http://lnkd.in/p/test", "https://user:pass@lnkd.in/p/test",
                     "https://lnkd.in:444/p/test", "https://lnkd.in/not-a-post"):
            with self.subTest(link=link), self.assertRaises(ValueError):
                linkedin_posts.resolve_copied_link(page, link)
        page.context.request.get.assert_not_called()

    def test_cancel_before_discovery_makes_no_browser_calls(self):
        stop = threading.Event()
        stop.set()
        page = Mock()
        with self.assertRaises(KeyboardInterrupt):
            linkedin_posts.collect_links(page, 10, stop)
        page.locator.assert_not_called()

    def test_uas_login_stops_with_login_message(self):
        page = Mock(url="https://www.linkedin.com/uas/login?session_redirect=test")
        page.is_closed.return_value = False
        with self.assertRaisesRegex(reader.AccessBlocked, "LinkedIn requires login"):
            reader.check_access(page)

    def test_checkpoint_naming_and_post_source(self):
        self.assertTrue(reader.daily_output_path(linkedin_posts.DEFAULT_SEARCH).name.startswith("linkedin_posts_"))
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            args = SimpleNamespace(output=Path(folder)/"posts.json", fresh=False, limit=10)
            result = {"jobs": [], "errors": []}
            reader.prepare_output(args, result, reader.search_url(linkedin_posts.DEFAULT_SEARCH))
            self.assertEqual(result["source"], "linkedin_posts")
            reader.validate_checkpoint(result, linkedin_posts.DEFAULT_SEARCH)

    def test_dashboard_accepts_post_search_with_three_workers(self):
        with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
            stop = threading.Event()
            def execute(args):
                stop.wait(2)
                return {"status": "interrupted"}, 130
            manager = dashboard.Manager(folder, execute=execute, bootstrap=lambda: None)
            try:
                manager.start({"url": linkedin_posts.DEFAULT_SEARCH, "limit": 10, "delay": 1, "workers": 3})
                self.assertEqual(manager.args.workers, 3)
                self.assertEqual(dashboard.source_name(manager.args.url), "linkedin_posts")
                self.assertTrue(manager.args.output.name.startswith("linkedin_posts_"))
            finally:
                stop.set()
                manager.thread.join(3)


if __name__ == "__main__":
    unittest.main()
