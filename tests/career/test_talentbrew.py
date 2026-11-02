import unittest
from unittest.mock import patch

from backend.fetchers import talentbrew

ROOT = "https://careers.example.com"


def card(job_id, title, location):
    return (f'<a class="sr-job-link" href="/job/x/{job_id}" data-job-id="{job_id}"><h2>{title}</h2>'
            f'<span class="job-location"><img alt="pin">{location}</span></a>')


def page(*cards):
    return {"results": "<section id='search-results'>" + "".join(cards) + "</section>", "hasJobs": bool(cards)}


class ParseTests(unittest.TestCase):
    def test_keeps_india_and_drops_foreign_or_unknown(self):
        html = page(card("1", "Analyst", "Noida, India"), card("2", "Eng", "Austin, United States"),
                    card("3", "Ops", "Remote"), card("4", "DA", "Bengaluru, Karnataka"),
                    card("5", "BI", "Indiana, United States"))["results"]
        jobs, skipped = talentbrew.parse_results(html, ROOT)
        self.assertEqual([j["source_id"] for j in jobs], ["1", "4"])
        self.assertEqual(jobs[1]["location"], "Bengaluru, Karnataka, India")  # Moody's-style label
        self.assertEqual(jobs[0]["url"], ROOT + "/job/x/1")
        self.assertEqual(skipped, 3)

    def test_missing_title_is_an_error(self):
        with self.assertRaises(ValueError):
            talentbrew.parse_results('<a href="/j" data-job-id="9"><span class="job-location">Pune, India</span></a>', ROOT)


class FetchTests(unittest.TestCase):
    cfg = {"company": "acme", "host": "careers.example.com", "org_id": 7}
    detail = '<div class="ats-description"><p>Python and SQL</p></div>'

    def run_fetch(self, pages, detail=None):
        with patch.object(talentbrew, "get_json", side_effect=pages), \
                patch.object(talentbrew, "get_text", return_value=self.detail if detail is None else detail), \
                patch.object(talentbrew.time, "sleep"):
            return talentbrew.fetch(self.cfg)

    def test_paginates_dedupes_and_reads_descriptions(self):
        result = self.run_fetch([page(card("1", "A", "Pune, India"), card("2", "B", "Noida, India")),
                                 page(card("2", "B", "Noida, India"), card("3", "C", "Delhi, India")), page()])
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["1", "2", "3"])
        self.assertEqual(result[0]["company"], "acme")
        self.assertEqual(result[0]["description"], "Python and SQL")

    def test_missing_description_is_partial_not_dropped(self):
        result = self.run_fetch([page(card("1", "A", "Pune, India")), page()], detail="<p>nothing</p>")
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("description unavailable: 1", result.error)

    def test_repeated_page_stops_with_partial(self):
        same = page(card("1", "A", "Pune, India"))
        result = self.run_fetch([same, same])
        self.assertEqual(result.status, "partial")
        self.assertIn("repeated listing page", result.error)

    def test_unavailable_first_page_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([None])

    def test_only_foreign_rows_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([page(card("1", "A", "Austin, United States")), page()])

    def test_later_page_failure_keeps_earlier_jobs(self):
        result = self.run_fetch([page(card("1", "A", "Pune, India")), None])
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
