"""Offline checks for the bounded Internshala jobs search."""

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
    def test_collect_fetches_jobs_only(self):
        mixed_page = page(1) + page(2).replace('/job/2', '/internship/detail/2')
        with patch.object(internshala, "SEARCHES", (("jobs/salary-6", 1),)), \
             patch.object(internshala, "_get", return_value=mixed_page) as get, \
             patch.object(internshala.time, "sleep"):
            result = internshala.collect()
        self.assertEqual(result.status, "ok")
        self.assertEqual([job["source_id"] for job in result], ["1"])
        self.assertEqual(result[0]["url"], "https://internshala.com/job/1")
        self.assertEqual(result[0]["description"], "Python and SQL")
        get.assert_called_once_with("jobs/salary-6", 1)

    def test_later_page_failure_is_partial(self):
        with patch.object(internshala, "_get", side_effect=[page(1), None]), \
             patch.object(internshala.time, "sleep"):
            result = internshala._fetch_search("jobs/salary-6", 2, set())
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("page 2 request failed", result.error)

    def test_jobs_search_failure_is_not_empty_success(self):
        with patch.object(internshala, "_get", return_value=None) as get, \
             self.assertLogs("jobbot", level="ERROR"):
            with self.assertRaisesRegex(RuntimeError, "all searches failed"):
                internshala.collect()
        get.assert_called_once_with("jobs/salary-6", 1)


if __name__ == "__main__":
    unittest.main()
