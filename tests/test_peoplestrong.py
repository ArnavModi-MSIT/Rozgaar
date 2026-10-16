import time
import unittest
from unittest.mock import patch

from core.experience import extract_min_experience
from fetchers import peoplestrong as ps


CFG = dict(company="mathco", host="mathco-careers.peoplestrong.com")


def row(code="MCP/D/1", country="India"):
    return dict(jobCode=code, jobTitle="Data Scientist", locationHierarchyComplete=country + ">Karnataka>Bangalore",
                jobDetailUrl="https://mathco-careers.peoplestrong.com/job/detail/" + code.replace("/", "_"))


def detail(code="MCP/D/1", country="India", minimum="0"):
    return dict(response=dict(requisitionCode=code, jobTitle="Data Scientist",
                             locationHierarchyComplete=country + ">Karnataka>Bangalore",
                             jobDescription="<p>" + "Introduction " * 1000 + "</p><p>Required qualifications at the end</p>",
                             minimumExp=minimum, maximumExp="2"))


class PeopleStrongTests(unittest.TestCase):
    def test_pagination_counts_foreign_but_retains_only_india(self):
        pages = [dict(totalRecords=2, response=[row(country="US")]),
                 dict(totalRecords=2, response=[row("MCP/D/2")])]
        with patch.object(ps, "post_json", side_effect=pages) as post, patch.object(ps, "get_json", return_value=detail("MCP/D/2")):
            result = ps.fetch(CFG)
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["MCP/D/2"])
        self.assertEqual(post.call_args_list[1].kwargs["params"]["offset"], 20)
        self.assertEqual(result[0]["location"], "Bangalore, Karnataka, India")
        self.assertIn("qualifications at the end", result[0]["description"])
        self.assertGreater(len(result[0]["description"]), 6000)
        self.assertEqual(extract_min_experience(result[0]["description"]), 0)

    def test_source_minimum_reaches_experience_parser(self):
        with patch.object(ps, "post_json", return_value=dict(totalRecords=1, response=[row()])), patch.object(ps, "get_json", return_value=detail(minimum="1")):
            result = ps.fetch(CFG)
        self.assertEqual(extract_min_experience(result[0]["description"]), 1)

    def test_empty_board_and_failure_are_distinct(self):
        with patch.object(ps, "post_json", return_value=dict(totalRecords=0, response=[])):
            self.assertEqual(ps.fetch(CFG).status, "ok")
        with patch.object(ps, "post_json", return_value=None):
            with self.assertRaises(RuntimeError):
                ps.fetch(CFG)

    def test_repeated_page_is_partial(self):
        with patch.object(ps, "post_json", return_value=dict(totalRecords=2, response=[row()])), patch.object(ps, "get_json", return_value=detail()):
            result = ps.fetch(CFG)
        self.assertEqual(result.status, "partial")
        self.assertIn("received 1 of 2", result.error)

    def test_wrong_detail_not_used(self):
        with patch.object(ps, "post_json", return_value=dict(totalRecords=1, response=[row()])), patch.object(ps, "get_json", return_value=detail("WRONG")):
            result = ps.fetch(CFG)
        self.assertEqual(result.status, "partial")
        self.assertEqual(result[0]["description"], "")
        self.assertIn("identity mismatch", result.error)

    def test_detail_foreign_country_dropped(self):
        with patch.object(ps, "post_json", return_value=dict(totalRecords=1, response=[row()])), patch.object(ps, "get_json", return_value=detail(country="US")):
            with self.assertRaisesRegex(RuntimeError, "country is not India"):
                ps.fetch(CFG)

    def test_expired_deadline_does_not_request(self):
        with patch.object(ps, "post_json") as post:
            with self.assertRaisesRegex(RuntimeError, "deadline"):
                ps.fetch(CFG, time.monotonic() - 1)
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
