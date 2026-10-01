import unittest
from unittest.mock import patch

from fetchers import google_careers


def page(total, job_id=None):
    card = (f'<div class="sMn82b"><h3 class="QJPWVe">Analyst</h3>'
            f'<a class="WpHeLc" href="jobs/results/{job_id}-analyst">Open</a></div>') if job_id else ""
    return f"<html><body>{total} jobs matched{card}</body></html>"


class GoogleCareersTests(unittest.TestCase):
    @patch("fetchers.google_careers._get")
    def test_both_searches_deduplicate(self, get):
        get.side_effect = [page(1, "123"), page(1, "123")]
        result = google_careers.collect([
            {"location": "India", "target_levels": []},
            {"location": "India", "target_levels": ["EARLY"], "e": "72477625"},
        ])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertIn("e=72477625&target_level=EARLY&location=India", get.call_args_list[1].args[0])

    @patch("fetchers.google_careers._get")
    def test_failed_second_search_is_partial(self, get):
        get.side_effect = [page(1, "123"), None]
        result = google_careers.collect([{"location": "India"}, {"location": "India", "target_levels": ["EARLY"]}])
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)

    @patch("fetchers.google_careers._get", return_value=page(0))
    def test_zero_results_is_valid(self, _get):
        result = google_careers.collect([{"location": "India"}])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 0)
