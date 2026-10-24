import unittest
from unittest.mock import patch
from backend.fetchers import zs

class ZSTests(unittest.TestCase):
    def test_pages(self):
        def job(n):
            return {"data": {"req_id": str(n), "slug": str(n), "title": "Analyst", "location_name": "Pune, India", "description": "<p>Python SQL</p>"}}
        with patch.object(zs.icims, "_fetch_page", side_effect=[{"totalCount": 2, "jobs": [job(1)]}, {"totalCount": 2, "jobs": [job(2)]}]):
            r = zs.collect()
        self.assertEqual(len(r), 2)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r[0]["url"], "https://jobs.zs.com/all/jobs/1")

    def test_failure_and_empty(self):
        with patch.object(zs.icims, "_fetch_page", return_value=None):
            with self.assertRaises(RuntimeError):
                zs.collect()
        with patch.object(zs.icims, "_fetch_page", return_value={"jobs": [], "totalCount": 0}):
            self.assertEqual(zs.collect().status, "ok")
