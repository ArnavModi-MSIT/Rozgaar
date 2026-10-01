import sqlite3
import unittest
from unittest.mock import patch

from core.storage import init_db, refresh_mastercard_from_workday
from fetchers import mastercard_workday


FACETS = {"facets": [{"facetParameter": "locationMainGroup", "values": [{
    "facetParameter": "locations", "values": [
        {"descriptor": "Pune, India", "id": "india-id"},
        {"descriptor": "Remote - Indiana", "id": "indiana-id"},
    ],
}]}]}


def row(number):
    return {"title": f"Analyst {number}", "locationsText": "Pune, India",
            "bulletFields": [f"R-{number}"],
            "externalPath": f"/job/Pune-India/Analyst_R-{number}"}


class MastercardWorkdayTests(unittest.TestCase):
    @patch("fetchers.mastercard_workday._description", return_value="Full role description")
    @patch("fetchers.mastercard_workday._request_page")
    def test_all_india_pages_and_shared_identity(self, request_page, _description):
        request_page.side_effect = [FACETS, {"total": 3, "jobPostings": [row(1), row(2)]},
                                    {"total": 0, "jobPostings": [row(3)]}]
        with patch.object(mastercard_workday, "PAGE_SIZE", 2), patch.object(mastercard_workday.time, "sleep"):
            result = mastercard_workday.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["source_id"], "R-1")
        self.assertEqual(result[0]["description"], "Full role description")
        self.assertIn("/en-US/CorporateCareers/job/Pune-India/", result[0]["url"])
        self.assertEqual(request_page.call_args_list[1].args[2], {"locations": ["india-id"]})

    @patch("fetchers.mastercard_workday._description", return_value="Full role description")
    @patch("fetchers.mastercard_workday._request_page")
    def test_missing_second_page_is_partial(self, request_page, _description):
        request_page.side_effect = [FACETS, {"total": 3, "jobPostings": [row(1), row(2)]}, None]
        with patch.object(mastercard_workday, "PAGE_SIZE", 2), patch.object(mastercard_workday.time, "sleep"):
            result = mastercard_workday.collect()
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 2)
        self.assertIn("listing page 2 failed", result.error)

    def test_refreshes_matching_phenom_row_without_losing_dismissal(self):
        conn = sqlite3.connect(":memory:")
        try:
            init_db(conn)
            conn.execute(
                "INSERT INTO jobs (id,company,title,location,url,description,source,first_seen,dismissed,category,skills,experience_years) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                ("mastercard:R-1", "mastercard", "Old title", "Pune, India", "https://careers.mastercard.com/old",
                 "Teaser", "phenom", 1, 1, "Other", "SQL", 2),
            )
            job = {"title": "Analyst", "location": "Pune, India", "url": "https://mastercard.wd1.myworkdayjobs.com/job/1",
                   "description": "Full role description"}
            self.assertTrue(refresh_mastercard_from_workday(conn, "mastercard:R-1", job))
            self.assertFalse(refresh_mastercard_from_workday(conn, "mastercard:R-1", job))
            saved = conn.execute("SELECT source,description,dismissed,category,skills,experience_years FROM jobs WHERE id='mastercard:R-1'").fetchone()
            self.assertEqual(saved, ("mastercard_workday", "Full role description", 1, None, None, None))
        finally:
            conn.close()
