"""Offline contract tests for the bounded public LinkedIn collector."""

import unittest
from unittest.mock import patch

from fetchers import linkedin


SEARCH_HTML = """
<div class="job-search-card" data-entity-urn="urn:li:jobPosting:123">
  <a class="base-card__full-link" href="https://in.linkedin.com/jobs/view/example-123?trackingId=x"></a>
  <h3 class="base-search-card__title">Data Engineer</h3>
  <h4 class="base-search-card__subtitle">Example Co</h4>
  <span class="job-search-card__location">Delhi, India</span>
</div>
"""
DETAIL_HTML = '<div class="show-more-less-html__markup"><p>Build Python pipelines.</p></div>'


class LinkedInTests(unittest.TestCase):
    def test_normalizes_card_and_public_description(self):
        with patch.object(linkedin, "_get", side_effect=[SEARCH_HTML, DETAIL_HTML]), \
             patch.object(linkedin.time, "sleep"):
            result = linkedin.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source_id"], "123")
        self.assertEqual(result[0]["company"], "Example Co")
        self.assertEqual(result[0]["url"], "https://in.linkedin.com/jobs/view/example-123")
        self.assertEqual(result[0]["description"], "Build Python pipelines.")

    def test_missing_description_is_partial(self):
        with patch.object(linkedin, "_get", side_effect=[SEARCH_HTML, None, None]), \
             patch.object(linkedin.time, "sleep"):
            result = linkedin.collect()
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("1 job descriptions unavailable", result.error)

    def test_both_search_routes_unavailable_fails(self):
        with patch.object(linkedin, "_get", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "searches unavailable"):
                linkedin.collect()
        with patch.object(linkedin, "_get", return_value="<html></html>"):
            with self.assertRaisesRegex(RuntimeError, "searches unavailable"):
                linkedin.collect()

    def test_guest_search_falls_back_to_public_page(self):
        with patch.object(linkedin, "_get", side_effect=[None, SEARCH_HTML, DETAIL_HTML]) as get, \
             patch.object(linkedin.time, "sleep"):
            result = linkedin.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertEqual(get.call_args_list[0].args[0], linkedin.GUEST_SEARCH_URL)
        self.assertEqual(get.call_args_list[1].args[0], linkedin.SEARCH_URL)

    def test_guest_detail_falls_back_to_public_job_page(self):
        with patch.object(linkedin, "_get", side_effect=[SEARCH_HTML, None, DETAIL_HTML]) as get, \
             patch.object(linkedin.time, "sleep"):
            result = linkedin.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(result[0]["description"], "Build Python pipelines.")
        self.assertEqual(get.call_args_list[-1].args[0], result[0]["url"])

    def test_guest_pagination_uses_offsets(self):
        cards = SEARCH_HTML * 10
        with patch.object(linkedin, "MAX_JOBS", 20), \
             patch.object(linkedin, "_get", side_effect=[cards, SEARCH_HTML]) as get:
            parsed, error = linkedin._search_cards()
        self.assertEqual(len(parsed), 11)
        self.assertEqual(error, "")
        self.assertEqual(get.call_args_list[0].kwargs["params"]["start"], 0)
        self.assertEqual(get.call_args_list[1].kwargs["params"]["start"], 10)


if __name__ == "__main__":
    unittest.main()
