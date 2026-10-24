import unittest
from unittest.mock import patch
from backend.fetchers import morgan_stanley_students as source

class StudentFeedTests(unittest.TestCase):
    def collect(self, data):
        with patch.object(source, "get_json", return_value=data):
            return source.collect()

    def test_india_description_and_identity(self):
        row = {"jobNumber": "20736", "jobTitle": "Industrial Trainee", "location": "Mumbai, India", "jobHtmlDescription": "<p>Currently pursuing a degree</p>", "qualification": "Required: SQL"}
        result = self.collect({"totalResults": 3, "resultSet": [row, dict(row), dict(row, jobNumber="2", location="Indianapolis, USA")]})
        self.assertEqual(len(result), 1)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result[0]["source_id"], "20736")
        self.assertIn("Required: SQL", result[0]["description"])
        self.assertTrue(result[0]["url"].endswith("/20736"))

    def test_empty_is_success(self):
        self.assertEqual(self.collect({"totalResults": 0, "resultSet": []}).status, "ok")

    def test_invalid_is_failure(self):
        for data in [None, {}, {"resultSet": None}]:
            with self.assertRaises(RuntimeError): self.collect(data)

    def test_truncated_or_missing_description_is_partial(self):
        result = self.collect({"totalResults": 2, "resultSet": [{"jobNumber": "1", "jobTitle": "Intern", "location": "India"}]})
        self.assertEqual(result.status, "partial")
        self.assertIn("description missing", result.error)
