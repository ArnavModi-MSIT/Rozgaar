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
        listing.side_effect = [{"jobsList": rows, "totalMatches": 20}, {"jobsList": [], "totalMatches": 0}]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 10)
        self.assertIn("received 10 of 20", result.error)

    @patch("backend.fetchers.bank_of_america.get_text", return_value='<div class="job-description-body__internal job__external">Role text</div>')
    @patch("backend.fetchers.bank_of_america.get_json")
    def test_reads_all_141_results(self, listing, detail):
        rows = [{"jobRequisitionId": str(i), "postingTitle": "Analyst", "location": "India", "jcrURL": f"/en-us/job-detail/{i}/analyst"} for i in range(141)]
        listing.side_effect = [{"jobsList": rows, "totalMatches": 141}, {"jobsList": [], "totalMatches": 0}]
        result = bank_of_america.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 141)
        self.assertEqual(detail.call_count, 141)
        self.assertEqual(listing.call_count, 2)
        self.assertEqual(listing.call_args_list[0].kwargs["params"]["rows"], bank_of_america.MAX_RESULTS_PER_SEARCH)


if __name__ == "__main__":
    unittest.main()
