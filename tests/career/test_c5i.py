import time
import unittest
from unittest.mock import patch

from backend.core.experience import extract_min_experience
from backend.fetchers import c5i


PAGE = '''<script>const nonce = "public-nonce";</script>
<div class="country-block" data-country="india"><i data-city="Bengaluru"></i><i data-city="Gurugram"></i><i data-city="Mumbai"></i><i data-city="Bengaluru"></i></div>
<div class="country-block" data-country="united-states"><i data-city="New Jersey"></i></div>'''


def response(rows, **extra):
    return dict(success=True, data=dict(code=200, data=dict(careersJobsList=rows, count=len(rows), hasNext=False, **extra)))


def row(sid=1, minimum=0, maximum=0):
    return dict(requisitionId=sid, requisitionTitle="Manager", yrsOfExpMin=minimum, yrsOfExpMax=maximum)


def detail(sid=1, text="Requirements: 5-12 years of experience"):
    return f'''<section class="job-details"><div class="heading_container"><h2>Manager</h2></div>
    <div class="job-description"><h2>Job Description</h2><p>{text}</p></div></section>
    <input name="requisitionId" value="{sid}">'''


class C5iTests(unittest.TestCase):
    def test_all_india_tabs_deduplicated_with_full_jd_and_no_zero_placeholder(self):
        calls = []
        def post(*args, **kwargs):
            calls.append(kwargs["files"]["city"][1])
            return response([row()])
        with patch.object(c5i, "get_text", side_effect=[PAGE, detail(text="Intro " * 2000 + " Requirements: 5-12 years of experience")]), patch.object(c5i, "post_json", side_effect=post):
            result = c5i.fetch(dict(company="c5i"))
        self.assertEqual(calls, ["Bengaluru", "Gurugram", "Mumbai"])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["location"], "Bengaluru, India; Gurugram, India; Mumbai, India")
        self.assertGreater(len(result[0]["description"]), 6000)
        self.assertNotIn("0-0 years", result[0]["description"])
        self.assertEqual(extract_min_experience(result[0]["description"]), 5)

    def test_failed_city_makes_other_city_jobs_partial(self):
        with patch.object(c5i, "get_text", side_effect=[PAGE, detail()]), patch.object(c5i, "post_json", side_effect=[response([row()]), None, response([])]):
            result = c5i.fetch(dict(company="c5i"))
        self.assertEqual(result.status, "partial")
        self.assertIn("Gurugram", result.error)

    def test_future_more_pages_not_reported_as_complete(self):
        page = response([row()]); page["data"]["data"]["hasNext"] = True
        page["data"]["data"]["count"] = 10
        with patch.object(c5i, "get_text", side_effect=[PAGE, detail()]), patch.object(c5i, "post_json", side_effect=[page, response([]), response([])]):
            result = c5i.fetch(dict(company="c5i"))
        self.assertEqual(result.status, "partial")
        self.assertIn("count mismatch", result.error)
        self.assertIn("additional city pages", result.error)

    def test_wrong_job_description_not_used(self):
        with patch.object(c5i, "get_text", side_effect=[PAGE, detail(sid=2)]), patch.object(c5i, "post_json", return_value=response([row()])):
            result = c5i.fetch(dict(company="c5i"))
        self.assertEqual(result.status, "partial")
        self.assertEqual(result[0]["description"], "")

    def test_explicit_zero_to_two_preserved(self):
        with patch.object(c5i, "get_text", side_effect=[PAGE, detail(text="Data analysis")]), patch.object(c5i, "post_json", return_value=response([row(minimum=0, maximum=2)])):
            result = c5i.fetch(dict(company="c5i"))
        self.assertEqual(extract_min_experience(result[0]["description"]), 0)

    def test_empty_vs_failed_vs_deadline(self):
        with patch.object(c5i, "get_text", return_value=PAGE), patch.object(c5i, "post_json", return_value=response([])):
            self.assertEqual(c5i.fetch(dict(company="c5i")).status, "ok")
        with patch.object(c5i, "get_text", return_value=None):
            with self.assertRaises(RuntimeError):
                c5i.fetch(dict(company="c5i"))
        with patch.object(c5i, "get_text") as get:
            with self.assertRaisesRegex(RuntimeError, "deadline"):
                c5i.fetch(dict(company="c5i"), time.monotonic() - 1)
        get.assert_not_called()
