import time
import unittest
from unittest.mock import patch

from core.experience import extract_min_experience
from fetchers import gem


CFG = dict(company="hasura", board="promptql", expected_team="PromptQL")


def row(sid="one", country="IND", title="Analyst"):
    return dict(id="internal-" + sid, extId=sid, title=title,
                locations=[dict(name="Remote", isoCountry=country)])


def listing(rows):
    return dict(data=dict(jobBoardExternal=dict(teamDisplayName="PromptQL"),
                          oatsExternalJobPostings=dict(jobPostings=rows)))


def detail(**changes):
    result = row()
    result.update(descriptionHtml="<p>" + "Intro " * 2000 + "</p><p>Role Requirements: 5+ years of experience</p>",
                  isUnlistedExternally=False, jobPostSectionHtml=dict(introHtml="<p>Intro header</p>", outroHtml="<p>Outro tail</p>"),
                  compensationHtml="<p>Compensation details</p>")
    result.update(changes)
    return dict(data=dict(oatsExternalJobPosting=result))


class GemTests(unittest.TestCase):
    def test_india_only_and_talent_community_excluded(self):
        rows = [row(), row("us", "USA"), row("pool", title="Join our Talent Community! ")]
        with patch.object(gem, "post_json", side_effect=[listing(rows), detail()]) as post:
            result = gem.fetch(CFG)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.status, "ok")
        self.assertEqual(post.call_count, 2)
        self.assertEqual(result[0]["location"], "Remote, India")
        self.assertGreater(len(result[0]["description"]), 6000)
        self.assertIn("Outro tail", result[0]["description"])
        self.assertIn("Compensation details", result[0]["description"])
        self.assertEqual(extract_min_experience(result[0]["description"]), 5)

    def test_empty_success_is_distinct_from_graphql_failure(self):
        with patch.object(gem, "post_json", return_value=listing([])):
            self.assertEqual(gem.fetch(CFG).status, "ok")
        payload = listing([]); payload["errors"] = [dict(message="Unavailable")]
        with patch.object(gem, "post_json", return_value=payload):
            with self.assertRaises(RuntimeError):
                gem.fetch(CFG)

    def test_wrong_employer_rejected(self):
        payload = listing([]); payload["data"]["jobBoardExternal"]["teamDisplayName"] = "Other employer"
        with patch.object(gem, "post_json", return_value=payload):
            with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
                gem.fetch(CFG)

    def test_mismatched_detail_not_used(self):
        with patch.object(gem, "post_json", side_effect=[listing([row()]), detail(extId="wrong")]):
            result = gem.fetch(CFG)
        self.assertEqual(result.status, "partial")
        self.assertEqual(result[0]["description"], "")

    def test_detail_country_and_unlisted_status_verified(self):
        for changes in [dict(locations=[dict(name="San Francisco", isoCountry="USA")]), dict(isUnlistedExternally=True)]:
            with self.subTest(changes=changes), patch.object(gem, "post_json", side_effect=[listing([row()]), detail(**changes)]):
                with self.assertRaises(RuntimeError):
                    gem.fetch(CFG)

    def test_expired_deadline_does_not_request(self):
        with patch.object(gem, "post_json") as post:
            with self.assertRaisesRegex(RuntimeError, "deadline"):
                gem.fetch(CFG, time.monotonic() - 1)
        post.assert_not_called()
