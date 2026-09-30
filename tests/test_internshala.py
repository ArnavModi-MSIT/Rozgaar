"""Offline checks for the three bounded Internshala searches."""

import unittest
from unittest.mock import patch

from fetchers import internshala


def page(*ids):
    return "".join(
        f'<div class="individual_internship" internshipid="{i}">'
        f'<a class="job-title-href" href="/job/{i}">Role {i}</a>'
        f'<p class="company-name">Company {i}</p>'
        f'<div class="locations"><span>Delhi</span></div>'
        f'<div class="about_job"><div class="text">Python and SQL</div></div>'
        '</div>'
        for i in ids
    )


class InternshalaTests(unittest.TestCase):
    def test_requested_searches_and_cross_search_dedup(self):
        responses = {
            ("internships", 1): page(1),
            ("jobs/salary-6", 1): page(1, 2),
            ("internships/stipend-10000", 1): page(1, 3),
        }
        with patch.object(internshala, "SEARCHES", tuple((path, 1) for path, _ in internshala.SEARCHES)), \
             patch.object(internshala, "_get", side_effect=lambda path, page_no: responses[(path, page_no)]), \
             patch.object(internshala.time, "sleep"):
            result = internshala.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual([job["source_id"] for job in result], ["1", "2", "3"])
        self.assertEqual(result[1]["url"], "https://internshala.com/job/2")
        self.assertEqual(result[1]["description"], "Python and SQL")

    def test_later_page_failure_is_partial(self):
        with patch.object(internshala, "_get", side_effect=[page(1), None]), \
             patch.object(internshala.time, "sleep"):
            result = internshala._fetch_search("jobs/salary-6", 2, set())
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("page 2 request failed", result.error)

    def test_one_search_failure_keeps_other_results(self):
        responses = {
            "internships": None,
            "jobs/salary-6": page(2),
            "internships/stipend-10000": page(3),
        }
        with patch.object(internshala, "SEARCHES", tuple((path, 1) for path, _ in internshala.SEARCHES)), \
             patch.object(internshala, "_get", side_effect=lambda path, page_no: responses[path]), \
             patch.object(internshala.time, "sleep"), \
             self.assertLogs("jobbot", level="ERROR"):
            result = internshala.collect()
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 2)
        self.assertIn("internships: page 1 request failed", result.error)


if __name__ == "__main__":
    unittest.main()
