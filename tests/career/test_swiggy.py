import base64
import json
import unittest
from unittest.mock import patch
from backend.fetchers import swiggy

class SwiggyTests(unittest.TestCase):
    def test_feed_and_link(self):
        row = {"reqId": 12, "reqTitle": "Data Analyst", "location": "Bengaluru", "jdDisplay": "<p>Python SQL</p>", "expMin": 0}
        with patch.object(swiggy, "post_json", return_value={"reqDetailsBOList": [row, row]}):
            r = swiggy.collect()
        self.assertEqual(len(r), 1)
        self.assertEqual(r.status, "ok")
        self.assertIn("Python SQL", r[0]["description"])
        context = json.loads(base64.b64decode(r[0]["url"].split("&p=")[1]))
        self.assertEqual(context["reqId"], 12)
        self.assertEqual(context["pageType"], "jd")

    def test_empty_and_failed(self):
        with patch.object(swiggy, "post_json", return_value={"reqDetailsBOList": []}):
            self.assertEqual(swiggy.collect().status, "ok")
        with patch.object(swiggy, "post_json", return_value=None):
            with self.assertRaises(RuntimeError):
                swiggy.collect()

    def test_missing_description(self):
        with patch.object(swiggy, "post_json", return_value={"reqDetailsBOList": [{"reqId": 1, "reqTitle": "Analyst"}]}):
            self.assertEqual(swiggy.collect().status, "partial")
