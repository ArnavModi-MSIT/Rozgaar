"""Workable fetch goes through the shared retry helper, so a rate limit is
retried instead of being read as "this board does not exist"."""

import unittest
from unittest.mock import patch

import requests

from backend.fetchers import workable


class Resp:
    def __init__(self, status, payload=None, headers=None):
        self.status_code = status
        self.payload = payload
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


BOARD = {"name": "Tiger", "jobs": [{
    "title": "Analyst", "shortcode": "AB1", "country": "India", "city": "Chennai", "description": "JD",
}]}


class WorkableRetryTests(unittest.TestCase):
    def fetch(self, responses, slug="tiger-analytics"):
        with patch.object(workable.SESSION, "request", side_effect=responses) as call, \
             patch("backend.fetchers.http_client.time.sleep"):
            try:
                return workable.fetch_workable(slug), call
            except RuntimeError as exc:
                return exc, call

    def test_rate_limit_is_retried_then_succeeds(self):
        result, call = self.fetch([Resp(429, headers={"Retry-After": "0"}), Resp(200, BOARD)])
        self.assertEqual([j["source_id"] for j in result], ["AB1"])
        self.assertEqual(call.call_count, 2)

    def test_persistent_rate_limit_fails_the_board_with_its_slug(self):
        result, call = self.fetch([Resp(429, headers={"Retry-After": "0"})] * 3)
        self.assertIsInstance(result, RuntimeError)
        self.assertIn("tiger-analytics", str(result))
        self.assertEqual(call.call_count, 3)

    def test_missing_board_is_not_retried(self):
        result, call = self.fetch([Resp(404)])
        self.assertIsInstance(result, RuntimeError)
        self.assertEqual(call.call_count, 1)

    def test_empty_board_is_valid(self):
        result, _ = self.fetch([Resp(200, {"name": "Amagi", "jobs": []})], slug="amagi")
        self.assertEqual(list(result), [])

    def test_timeout_is_retried(self):
        result, call = self.fetch([requests.Timeout("slow"), Resp(200, BOARD)])
        self.assertEqual(len(result), 1)
        self.assertEqual(call.call_count, 2)


if __name__ == "__main__":
    unittest.main()
