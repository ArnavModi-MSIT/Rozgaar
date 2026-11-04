"""A non-retryable 4xx returns None but says which status it was."""

import logging
import unittest
from unittest.mock import patch

import requests

from backend.fetchers import http_client


class Resp:
    def __init__(self, status):
        self.status_code = status
        self.headers = {}

    def json(self):
        return {}

    def raise_for_status(self):
        raise requests.HTTPError(str(self.status_code))


class RejectionLoggingTests(unittest.TestCase):
    def call(self, status):
        session = requests.Session()
        with patch.object(session, "request", return_value=Resp(status)) as req:
            result = http_client.get_json(session, "https://example.com/x")
        return result, req.call_count

    def test_403_is_not_retried_and_logs_a_warning_with_status(self):
        with self.assertLogs("jobbot", level="WARNING") as logs:
            result, calls = self.call(403)
        self.assertIsNone(result)
        self.assertEqual(calls, 1)
        self.assertIn("HTTP 403", logs.output[0])
        self.assertIn("https://example.com/x", logs.output[0])

    def test_404_logs_at_info_only(self):
        with self.assertLogs("jobbot", level="INFO") as logs:
            result, calls = self.call(404)
        self.assertIsNone(result)
        self.assertEqual(calls, 1)
        self.assertEqual(logs.records[0].levelno, logging.INFO)
        self.assertIn("HTTP 404", logs.output[0])


if __name__ == "__main__":
    unittest.main()
