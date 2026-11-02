import unittest
from unittest.mock import patch

from backend.fetchers import capgemini

CFG = {"company": "capgemini"}


def row(i, title="Data Engineer", code="en-in", desc="Build pipelines in SQL.", loc="Noida, Pune"):
    return {"id": f"{i}-en_GB", "title": title, "country_code": code, "location": loc, "description_stripped": desc,
            "experience_level": "Experienced Professionals", "apply_job_url": f"https://careers.capgemini.com/job/x/{i}"}


def page(rows, total):
    return {"data": rows, "total": total}


class CapgeminiTests(unittest.TestCase):
    def run_fetch(self, pages):
        with patch.object(capgemini, "get_json", side_effect=pages), patch.object(capgemini.time, "sleep"):
            return capgemini.fetch(CFG)

    def test_parse_row_normalises_location_and_description(self):
        job = capgemini.parse_row(row(1, loc="Noida,  Pune"))
        self.assertEqual(job["location"], "Noida, Pune, India")
        self.assertIn("Experience level: Experienced Professionals", job["description"])
        self.assertEqual(job["url"], "https://careers.capgemini.com/job/x/1")

    def test_foreign_country_code_is_not_claimed(self):
        self.assertIsNone(capgemini.parse_row(row(1, code="en-gb")))

    def test_bad_identity_or_foreign_host_raises(self):
        bad = row(1)
        bad["apply_job_url"] = "https://evil.example.org/job/1"
        with self.assertRaises(ValueError):
            capgemini.parse_row(bad)

    def test_pages_are_followed_and_deduped(self):
        full = [row(i) for i in range(capgemini.PAGE_SIZE)]
        result = self.run_fetch([page(full, 103), page([row(0), row(100), row(101), row(102)], 103)])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 103)
        self.assertEqual(result[0]["company"], "capgemini")

    def test_missing_description_is_partial(self):
        result = self.run_fetch([page([row(1, desc="")], 1)])
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)
        self.assertIn("description unavailable: 1-en_GB", result.error)

    def test_first_page_unavailable_raises_and_later_failure_keeps_jobs(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([None])
        full = [row(i) for i in range(capgemini.PAGE_SIZE)]
        result = self.run_fetch([page(full, 250), None])
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), capgemini.PAGE_SIZE)


if __name__ == "__main__":
    unittest.main()
