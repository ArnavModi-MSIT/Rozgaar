import unittest
from unittest.mock import patch

from backend.fetchers import mckinsey

CFG = {"company": "mckinsey"}


def doc(job_id="1", title="Analyst", cities=("Bengaluru", "London", "Gurugram"), countries=("India", "United Kingdom", "India"),
        body="<p>Analyse data.</p>"):
    return {"jobID": job_id, "title": title, "friendlyURL": f"analyst-{job_id}", "cities": list(cities), "countries": list(countries),
            "whatYouWillDo": body, "whoYouWillWorkWith": "<p>Teams.</p>", "yourBackground": "<ul><li>SQL</li></ul>",
            "compensationRange": "$189,000 - $189,000"}


def page(docs, found=None):
    return {"docs": docs, "numFound": found if found is not None else len(docs)}


class McKinseyTests(unittest.TestCase):
    def run_fetch(self, pages):
        with patch.object(mckinsey, "get_json", side_effect=pages), patch.object(mckinsey.time, "sleep"):
            return mckinsey.fetch(CFG)

    def test_keeps_only_india_cities_of_a_global_role(self):
        job = mckinsey.parse_doc(doc())
        self.assertEqual(job["location"], "Bengaluru, India; Gurugram, India")
        self.assertEqual(job["url"], "https://www.mckinsey.com/careers/search-jobs/jobs/analyst-1")
        self.assertIn("Analyse data", job["description"])
        self.assertIn("SQL", job["description"])
        self.assertNotIn("$", job["description"])  # compensation is never copied

    def test_no_india_city_is_skipped_and_misaligned_arrays_are_rejected(self):
        self.assertIsNone(mckinsey.parse_doc(doc(cities=("London",), countries=("United Kingdom",))))
        with self.assertRaises(ValueError):
            mckinsey.parse_doc(doc(cities=("Pune", "London"), countries=("India",)))
        bad = doc()
        bad["friendlyURL"] = "../x"
        with self.assertRaises(ValueError):
            mckinsey.parse_doc(bad)

    def test_pages_followed_until_short_page(self):
        full = [doc(str(i)) for i in range(mckinsey.PAGE_SIZE)]
        result = self.run_fetch([page(full, 22), page([doc("20"), doc("21")], 22)])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 22)

    def test_unavailable_first_page_raises_and_later_failure_is_partial(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([None])
        full = [doc(str(i)) for i in range(mckinsey.PAGE_SIZE)]
        result = self.run_fetch([page(full, 40), None])
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), mckinsey.PAGE_SIZE)


if __name__ == "__main__":
    unittest.main()
