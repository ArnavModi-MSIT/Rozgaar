import unittest
from unittest.mock import patch
from fetchers import zepto

ROW={"id":"one","title":"Engineer","locations":"Bengaluru, Karnataka\r, India","jd":"&lt;p&gt;Python SQL&lt;/p&gt;"}
class ZeptoTests(unittest.TestCase):
    def test_normalization(self):
        job=zepto.normalize(ROW)
        self.assertEqual(job["description"],"Python SQL")
        self.assertEqual(job["location"],"Bengaluru, Karnataka, India")
        self.assertTrue(job["url"].endswith("/jobDetails/one"))
    def test_verified_empty(self):
        with patch.object(zepto,"get_text",return_value="page"),patch.object(zepto,"post_json",return_value={"status":"success","data":[],"job_counts":0}):
            result=zepto.collect()
        self.assertEqual(result.status,"ok")
        self.assertEqual(len(result),0)
    def test_failed_feed_is_not_empty_success(self):
        with patch.object(zepto,"get_text",return_value="page"),patch.object(zepto,"post_json",return_value=None):
            with self.assertRaises(RuntimeError):zepto.collect()
    def test_interrupted_pagination_preserves_partial_jobs(self):
        with patch.object(zepto,"get_text",return_value="page"),patch.object(zepto,"post_json",side_effect=[{"status":"success","data":[ROW],"job_counts":2},None]):
            result=zepto.collect()
        self.assertEqual(result.status,"partial")
        self.assertEqual(len(result),1)
