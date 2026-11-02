import unittest
from unittest.mock import patch

from backend.fetchers import bank_of_america


class BankOfAmericaTests(unittest.TestCase):
    @patch("backend.fetchers.bank_of_america.get_text", return_value='<div class="job-description-body__internal job__external">Python analyst role</div>')
    @patch("backend.fetchers.bank_of_america.get_json")
    def test_general_and_empty_student_search(self, listing, detail):
        listing.side_effect = [
            {"jobsList": [{"jobRequisitionId": "123", "postingTitle": "Analyst", "location": "Mumbai, India", "jcrURL": "/en-us/job-detail/123/analyst"}], "totalMatches": 1},
            {"jobsList": [], "totalMatches": 0},
        ]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["description"], "Python analyst role")
        self.assertEqual(result[0]["source_id"], "123")
        self.assertEqual(detail.call_count, 1)

    @patch("backend.fetchers.bank_of_america.get_text", return_value='<div class="job-description-body__internal job__external">Role text</div>')
    @patch("backend.fetchers.bank_of_america.get_json")
    def test_incomplete_response_is_partial(self, listing, _detail):
        rows = [{"jobRequisitionId": str(i), "postingTitle": "Analyst", "location": "India", "jcrURL": f"/en-us/job-detail/{i}/analyst"} for i in range(10)]
        listing.side_effect = [{"jobsList": rows, "totalMatches": 20}, {"jobsList": [], "totalMatches": 20}, {"jobsList": rows, "totalMatches": 20}, {"jobsList": [], "totalMatches": 0}]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 10)
        self.assertIn("received 10 of 20", result.error)

    @patch("backend.fetchers.bank_of_america.get_text", return_value='<div class="job-description-body__internal job__external">Role text</div>')
    @patch("backend.fetchers.bank_of_america.get_json")
    def test_reads_all_141_results(self, listing, detail):
        rows = [{"jobRequisitionId": str(i), "postingTitle": "Analyst", "location": "India", "jcrURL": f"/en-us/job-detail/{i}/analyst"} for i in range(141)]
        listing.side_effect = [{"jobsList": rows[:100], "totalMatches": 141}, {"jobsList": rows[100:], "totalMatches": 141}, {"jobsList": [], "totalMatches": 0}]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 141)
        self.assertEqual(detail.call_count, 141)
        self.assertEqual(listing.call_count, 3)
        self.assertEqual([c.kwargs["params"]["start"] for c in listing.call_args_list[:2]], [0, 100])
        self.assertEqual(listing.call_args_list[0].kwargs["params"]["rows"], bank_of_america.PAGE_SIZE)

    @patch("backend.fetchers.bank_of_america.get_text", return_value='<div class="job-description-body__internal job__external">Role text</div>')
    @patch("backend.fetchers.bank_of_america.get_json")
    def test_timeout_after_first_page_is_partial(self, listing, _detail):
        rows = [{"jobRequisitionId": str(i), "postingTitle": "Analyst", "location": "India", "jcrURL": f"/en-us/job-detail/{i}/analyst"} for i in range(100)]
        listing.side_effect = [{"jobsList": rows, "totalMatches": 150}, None, {"jobsList": [], "totalMatches": 0}]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 100)
        self.assertIn("listing request failed at offset 100", result.error)

    @patch("backend.fetchers.bank_of_america.get_json", return_value=None)
    def test_total_timeout_reports_request_failure(self, _listing):
        with self.assertRaisesRegex(RuntimeError, "listing request failed"):
            bank_of_america.collect()

    @patch("backend.fetchers.bank_of_america.get_text", return_value='<div class="job-description-body__internal job__external">Role text</div>')
    @patch("backend.fetchers.bank_of_america.get_json")
    def test_empty_second_page_falls_back_to_single_full_request(self, listing, _detail):
        rows = [{"jobRequisitionId": str(i), "postingTitle": "Analyst", "location": "India", "jcrURL": f"/en-us/job-detail/{i}/analyst"} for i in range(116)]
        listing.side_effect = [
            {"jobsList": rows[:100], "totalMatches": 116},
            {"jobsList": [], "totalMatches": 116},
            {"jobsList": rows, "totalMatches": 116},
            {"jobsList": [], "totalMatches": 0},
        ]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 116)
        self.assertEqual(listing.call_args_list[2].kwargs["params"], {"start": 0, "rows": 116, "search": "jobsByLocation", "searchstring": "India"})


if __name__ == "__main__":
    unittest.main()
