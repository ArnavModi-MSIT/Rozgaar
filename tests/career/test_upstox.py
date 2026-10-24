import unittest
from unittest.mock import patch

from backend.core.experience import extract_min_experience
from backend.fetchers import employer_portals as portals
from backend.fetchers.result import CollectionResult


def row(sid="one", published=1, country="India", title="Product Intern"):
    return dict(job_id=sid, job_title=title, post_on_careers_page=published,
                location_country=country, location=["Mumbai, " + country],
                experience_from="", experience_to="", employee_type="Intern")


def detail(sid="one", title="Product Intern", description="Complete internship description"):
    return dict(company="upstox", source_id=sid, title=title, location="Mumbai, India",
                url="https://upstox.darwinbox.in/ms/candidatev2/main/careers/jobDetails/" + sid,
                description=description)


class UpstoxTests(unittest.TestCase):
    def test_only_official_published_india_ids_and_matching_full_jds(self):
        rows = [row(), row("internal", 0), row("referral", 0), row("us", country="United States")]
        jd = "Intro " * 2000 + " Qualifications at the end."
        details = CollectionResult([detail(description=jd), detail("extra")])
        with patch.object(portals, "get_json", return_value=dict(success=True, data=rows)), patch.object(portals, "fetch_darwinbox", return_value=details):
            result = portals.fetch_upstox(dict(company="upstox"))
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["one"])
        self.assertIn("Qualifications at the end", result[0]["description"])
        self.assertGreater(len(result[0]["description"]), 6000)
        self.assertIsNone(extract_min_experience(result[0]["description"]))

    def test_header_experience_reaches_existing_parser(self):
        jd = "Job Title: Compliance\nExperience: 12+ years\nLocation: Mumbai\nAbout us\nResponsibilities"
        with patch.object(portals, "get_json", return_value=dict(success=True, data=[row()])), patch.object(portals, "fetch_darwinbox", return_value=CollectionResult([detail(description=jd)])):
            result = portals.fetch_upstox(dict(company="upstox"))
        self.assertEqual(extract_min_experience(result[0]["description"]), 12)

    def test_explicit_zero_to_two_preserved(self):
        listing = row(); listing.update(experience_from="0", experience_to="2")
        with patch.object(portals, "get_json", return_value=dict(success=True, data=[listing])), patch.object(portals, "fetch_darwinbox", return_value=CollectionResult([detail()])):
            result = portals.fetch_upstox(dict(company="upstox"))
        self.assertEqual(extract_min_experience(result[0]["description"]), 0)

    def test_wrong_detail_identity_does_not_import_wrong_description(self):
        with patch.object(portals, "get_json", return_value=dict(success=True, data=[row()])), patch.object(portals, "fetch_darwinbox", return_value=CollectionResult([detail(title="Other title")])):
            result = portals.fetch_upstox(dict(company="upstox"))
        self.assertEqual(result.status, "partial")
        self.assertEqual(result[0]["description"], "")

    def test_partial_board_not_reported_complete(self):
        with patch.object(portals, "get_json", return_value=dict(success=True, data=[row()])), patch.object(portals, "fetch_darwinbox", return_value=CollectionResult([detail()], status="partial", error="Page incomplete")):
            result = portals.fetch_upstox(dict(company="upstox"))
        self.assertEqual(result.status, "partial")
        self.assertIn("Page incomplete", result.error)

    def test_empty_and_failure_are_distinct(self):
        with patch.object(portals, "get_json", return_value=dict(success=True, data=[])), patch.object(portals, "fetch_darwinbox") as board:
            self.assertEqual(portals.fetch_upstox(dict(company="upstox")).status, "ok")
        board.assert_not_called()
        with patch.object(portals, "get_json", return_value=None):
            with self.assertRaises(RuntimeError):
                portals.fetch_upstox(dict(company="upstox"))
