import json
import unittest
from unittest.mock import patch
from backend.fetchers import deshaw, quadeye, rippling
from backend.core.collector import PLATFORMS

class NewCareerTests(unittest.TestCase):
    def test_registered(self):
        self.assertTrue({"rippling", "deshaw", "quadeye"}.issubset({name for name, _ in PLATFORMS}))

    def test_deshaw_excludes_exploratory(self):
        def job(n, exploratory):
            return {"data": {"id": n, "jobUrl": f"analyst-{n}", "displayName": "Analyst", "jobMetadata": {"isExploratory": exploratory, "jobLocations": [{"name": "Hyderabad"}]}, "jobDescription": {"websiteDescription": "Intro", "responsibilities": "Python SQL", "peopleWeAreLookingForHtml": "<p>Qualifications</p>"}}}
        html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({"props": {"pageProps": {"regularJobs": [job(1, False), job(2, True)], "jobsFetchingError": False}}}) + '</script>'
        with patch.object(deshaw, "get_text", return_value=html):
            r = deshaw.collect()
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["location"], "Hyderabad, India")
        self.assertIn("Qualifications", r[0]["description"])

    def test_quadeye_no_recruiter_metadata(self):
        data = {"success": True, "data": [{"id": "1", "Posting_Title": "Software Developer", "Country": "India", "Job_Location": ["Gurugram"], "Job_Description": "Python SQL", "Assigned_Recruiter": [{"email": "not-stored@example.invalid"}]}]}
        with patch.object(quadeye, "get_json", return_value=data):
            r = quadeye.collect()
        self.assertEqual(r.status, "ok")
        self.assertEqual(r[0]["location"], "Gurugram, India")
        self.assertNotIn("Assigned_Recruiter", r[0])

    def test_rippling_merges_locations_and_filters_countries(self):
        def hit(location, country="IN"):
            return {"jobId": "1", "name": "Engineer", "url": "https://ats.rippling.com/rippling/jobs/1", "locations": [{"name": location, "countryCode": country}]}
        pages = [{"hits": [hit("Bangalore"), hit("New York", "US")], "nbHits": 3, "nbPages": 2}, {"hits": [hit("Hyderabad")], "nbHits": 3, "nbPages": 2}]
        detail = '<script id="__NEXT_DATA__">' + json.dumps({"props": {"pageProps": {"apiData": {"jobPost": {"description": {"company": "<p>About company</p>", "role": "<p>Python SQL</p>"}}}}}}) + '</script>'
        with patch.object(rippling, "discover", return_value=("careers", "test", "public-test")), patch.object(rippling, "post_json", side_effect=pages), patch.object(rippling, "get_text", return_value=detail):
            r = rippling.collect()
        self.assertEqual(len(r), 1)
        self.assertEqual(r.status, "ok")
        self.assertIn("Bangalore", r[0]["location"])
        self.assertIn("Hyderabad", r[0]["location"])
        self.assertNotIn("New York", r[0]["location"])

    def test_failures_are_not_empty_success(self):
        with patch.object(deshaw, "get_text", return_value=None):
            with self.assertRaises(RuntimeError): deshaw.collect()
        with patch.object(quadeye, "get_json", return_value=None):
            with self.assertRaises(RuntimeError): quadeye.collect()
