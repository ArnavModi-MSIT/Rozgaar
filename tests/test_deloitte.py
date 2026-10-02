import unittest
from unittest.mock import patch
from fetchers import deloitte

class DeloitteTests(unittest.TestCase):
    def test_pagination_and_descriptions(self):
        def page(n):
            return f'<p>Results {n} – {n} of 2</p><table><tr class="data-row"><td><a class="jobTitle-link" href="/job/test/{n}/">Analyst</a><span class="jobLocation">Delhi, IN</span></td></tr></table>'
        with patch.object(deloitte.sf, "PAGE_SIZE", 1), patch.object(deloitte, "get_text", side_effect=[page(1), page(2)]) as get, patch.object(deloitte.sf, "fetch_job_description", return_value="Python SQL"):
            r = deloitte.collect()
        self.assertEqual(len(r), 2)
        self.assertEqual(r.status, "ok")
        self.assertIn("/718244/1/", get.call_args_list[1].args[1])
        self.assertEqual(r[0]["location"], "Delhi, India")
        self.assertNotIn("_href", r[0])

    def test_request_failure(self):
        with patch.object(deloitte, "get_text", return_value=None):
            with self.assertRaises(RuntimeError):
                deloitte.collect()

    def test_missing_description_partial(self):
        html = '<p>Results 1 – 1 of 1</p><tr class="data-row"><a class="jobTitle-link" href="/job/test/1/">Analyst</a></tr>'
        with patch.object(deloitte, "get_text", return_value=html), patch.object(deloitte.sf, "fetch_job_description", return_value=""):
            self.assertEqual(deloitte.collect().status, "partial")
