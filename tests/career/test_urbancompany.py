import unittest
from unittest.mock import patch

from backend.fetchers import urbancompany

CFG = {"company": "urbancompany"}


def row(job_id="a-1", title="Analyst", location=("Bangalore, Karnataka, India",), desc="<p>Build <b>dashboards</b>.</p>"):
    return {"job_id": job_id, "job_title": title, "location": list(location), "job_description": desc,
            "apply_url": f"https://urbancompany.turbohire.co/job/publicjobs/{job_id}"}


class UrbanCompanyTests(unittest.TestCase):
    def run_fetch(self, payload):
        with patch.object(urbancompany, "post_json", return_value=payload):
            return urbancompany.fetch(CFG)

    def test_parses_india_rows_and_strips_html(self):
        result = self.run_fetch({"jobs": [row(), row("b-2", location=("Gurgaon, Haryana, India", "Mumbai, India"))]})
        self.assertEqual(result.status, "ok")
        self.assertIn("Build dashboards", result[0]["description"])
        self.assertNotIn("<", result[0]["description"])
        self.assertEqual(result[1]["location"], "Gurgaon, Haryana, India; Mumbai, India")
        self.assertEqual(result[0]["company"], "urbancompany")

    def test_rows_without_india_evidence_are_dropped(self):
        result = self.run_fetch({"jobs": [row(), row("c-3", location=("Dubai, UAE",))]})
        self.assertEqual([j["source_id"] for j in result], ["a-1"])

    def test_missing_description_is_partial(self):
        result = self.run_fetch({"jobs": [row(desc="")]})
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result), 1)

    def test_foreign_apply_host_is_rejected_and_bad_payloads_raise(self):
        bad = row()
        bad["apply_url"] = "https://evil.example.org/x"
        with self.assertRaises(ValueError):
            urbancompany.parse_row(bad)
        with self.assertRaises(RuntimeError):
            self.run_fetch(None)
        with self.assertRaises(RuntimeError):
            self.run_fetch({"jobs": [row(location=("Dubai, UAE",))]})


if __name__ == "__main__":
    unittest.main()
