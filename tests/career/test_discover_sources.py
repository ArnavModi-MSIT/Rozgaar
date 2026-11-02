import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.career import discover_sources as ds


class SlugVariantTests(unittest.TestCase):
    def test_hints_first_and_noise_words_dropped(self):
        variants = ds.slug_variants("Pine Labs", ["pinelabs"])
        self.assertEqual(variants[0], "pinelabs")
        self.assertIn("pine", variants)
        self.assertIn("pine-labs", variants)
        self.assertEqual(len(variants), len(set(variants)))
        self.assertLessEqual(len(variants), 8)
        self.assertIn("pine", ds.slug_variants("Pine Labs Technologies India"))

    def test_punctuation_and_parentheses(self):
        self.assertIn("zomato", ds.slug_variants("Eternal (Zomato)", ["zomato"]))
        self.assertIn("dunbradstreet", ds.slug_variants("Dun & Bradstreet"))


class IndiaEvidenceTests(unittest.TestCase):
    def test_greenhouse(self):
        data = {"jobs": [{"title": "Analyst", "location": {"name": "Bengaluru, India"}},
                         {"title": "Engineer", "location": {"name": "Indiana, USA"}},
                         {"title": "Remote", "location": {"name": "Remote"}}]}
        self.assertEqual(ds.india_postings("greenhouse", data), (1, ["Analyst"]))

    def test_lever_uses_country_field(self):
        data = [{"text": "SDE", "country": "IN", "categories": {"location": "Pune"}},
                {"text": "PM", "country": "US", "categories": {"location": "New York"}}]
        self.assertEqual(ds.india_postings("lever", data), (1, ["SDE"]))

    def test_ashby_secondary_location_and_country(self):
        data = {"jobs": [{"title": "DA", "location": "Remote", "secondaryLocations": [{"location": "Hyderabad, India"}]},
                         {"title": "X", "location": "London", "address": {"postalAddress": {"addressCountry": "GB"}}}]}
        self.assertEqual(ds.india_postings("ashby", data), (1, ["DA"]))

    def test_smartrecruiters_and_workable(self):
        sr = {"content": [{"name": "Analyst", "location": {"country": "in"}}, {"name": "Other", "location": {"country": "us"}}]}
        self.assertEqual(ds.india_postings("smartrecruiters", sr), (1, ["Analyst"]))
        wk = {"jobs": [{"title": "QA", "locations": [{"countryCode": "IN"}]}, {"title": "Ops", "country": "France"}]}
        self.assertEqual(ds.india_postings("workable", wk), (1, ["QA"]))

    def test_malformed_payloads_are_zero(self):
        for group in ds.ALL_GROUPS:
            self.assertEqual(ds.india_postings(group, None), (0, []))
            self.assertEqual(ds.india_postings(group, {"unexpected": 1}), (0, []))


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status, payload, headers or {}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), 0

    def get(self, url, timeout=None):
        self.calls += 1
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FetchTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(ds.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("_wait_turn",):
            p = patch.object(ds, name)
            p.start()
            self.addCleanup(p.stop)

    def test_ok_missing_and_non_json(self):
        self.assertEqual(ds.fetch(FakeSession(FakeResponse(200, {"a": 1})), "u"), ("ok", {"a": 1}))
        self.assertEqual(ds.fetch(FakeSession(FakeResponse(404)), "u"), ("missing", None))
        self.assertEqual(ds.fetch(FakeSession(FakeResponse(200)), "u"), ("missing", None))

    def test_rate_limit_is_error_not_missing_and_recovers(self):
        limited = FakeResponse(429, headers={"Retry-After": "1"})
        self.assertEqual(ds.fetch(FakeSession(limited, limited, limited), "u"), ("error", None))
        self.assertEqual(ds.fetch(FakeSession(limited, FakeResponse(200, [1])), "u"), ("ok", [1]))

    def test_timeout_is_error(self):
        import requests
        session = FakeSession(requests.Timeout(), requests.ConnectionError(), requests.Timeout())
        self.assertEqual(ds.fetch(session, "u"), ("error", None))


class ProbeTests(unittest.TestCase):
    def test_first_board_with_india_postings_wins_and_misses_are_skipped(self):
        def fake_fetch(_session, url, **_kw):
            if "greenhouse" in url and "/acme/" in url:
                return "ok", {"jobs": [{"title": "US only", "location": {"name": "Austin, TX"}}]}  # no India
            if "lever.co" in url and url.split("postings/")[1].startswith("acme"):
                return "ok", [{"text": "Analyst", "country": "IN", "categories": {"location": "Mumbai"}}]
            return "missing", None
        with patch.object(ds, "fetch", fake_fetch):
            row, errors = ds.probe(None, {"name": "Acme"})
        self.assertEqual((row["group"], row["key"], row["india_postings"], errors), ("lever", "acme", 1, 0))
        self.assertEqual(row["career_url"], "https://jobs.lever.co/acme")

    def test_clean_misses_are_not_found_but_failures_are_inconclusive(self):
        with patch.object(ds, "fetch", return_value=("missing", None)):
            self.assertEqual(ds.probe(None, {"name": "Nobody Corp"}), (None, 0))
        with patch.object(ds, "fetch", return_value=("error", None)):
            row, errors = ds.probe(None, {"name": "Busy Corp"})
        self.assertIsNone(row)
        self.assertGreater(errors, 0)

    def test_workable_uses_few_slugs(self):
        urls = []
        def fake_fetch(_session, url, **_kw):
            urls.append(url)
            return "missing", None
        with patch.object(ds, "fetch", fake_fetch):
            ds.probe(None, {"name": "Some Long Company Name Here", "groups": ["workable"]})
        self.assertLessEqual(len(urls), 3)


class WorkflowTests(unittest.TestCase):
    def test_discover_report_and_idempotent_apply(self):
        def fake_probe(_session, candidate):
            if candidate["name"] == "Busy":
                return None, 2
            if candidate["name"] == "Acme":
                return {"key": "acme", "name": "Acme", "group": "greenhouse", "career_url": "https://job-boards.greenhouse.io/acme",
                        "india_postings": 2, "sample_titles": ["A", "B"], "skip": False}, 0
            if candidate["name"] == "Skipme":
                return {"key": "skipme", "name": "Skipme", "group": "lever", "career_url": "https://jobs.lever.co/skipme",
                        "india_postings": 1, "sample_titles": ["C"], "skip": False}, 0
            return None, 0
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            module = tmp / "career_discovered.py"
            module.write_text(ds.MODULE.read_text(encoding="utf-8"), encoding="utf-8")
            with patch.object(ds, "probe", fake_probe), patch.object(ds, "RESULTS", tmp / "r.json"), \
                    patch.object(ds, "REPORT", tmp / "r.md"), patch.object(ds, "MODULE", module):
                found, missing, already, inconclusive = ds.discover([{"name": "Acme"}, {"name": "Skipme"}, {"name": "Ghost Inc"}, {"name": "Atlan"}, {"name": "Busy"}])
                self.assertEqual([r["key"] for r in found], ["acme", "skipme"])
                self.assertEqual(missing, ["Ghost Inc"])
                self.assertEqual(already, ["Atlan"])  # already configured display name
                self.assertEqual(inconclusive, ["Busy"])
                ds.write_report(found, missing, already, inconclusive)
                report = (tmp / "r.md").read_text(encoding="utf-8")
                self.assertIn("Ghost Inc", report)
                self.assertIn("Busy", report)
                data = json.loads((tmp / "r.json").read_text(encoding="utf-8"))
                data["found"][1]["skip"] = True
                (tmp / "r.json").write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(ds.apply_results(), 1)
                namespace = {"GREENHOUSE": [], "LEVER": [], "ASHBY": [], "WORKABLE": [], "SMARTRECRUITERS": [], "DISPLAY_NAMES": {}}
                source = module.read_text(encoding="utf-8")
                scope = {}
                exec(compile(source, "career_discovered", "exec"), scope)
                scope["register"](namespace)
                self.assertEqual(namespace["GREENHOUSE"], ["acme"])
                self.assertEqual(namespace["LEVER"], [])
                self.assertEqual(scope["INDIA_BOARDS"], {"acme"})
                self.assertEqual(ds.apply_results(), 1)  # repeat run is stable


class CandidateListTests(unittest.TestCase):
    def test_candidate_file_is_valid_and_unique(self):
        rows = json.loads(ds.CANDIDATES.read_text(encoding="utf-8"))
        names = [r["name"] for r in rows]
        self.assertGreaterEqual(len(names), 100)
        self.assertEqual(len(names), len(set(names)))
        for row in rows:
            self.assertTrue(row["name"].strip())
            for slug in row.get("slugs", []):
                self.assertRegex(slug, r"^[A-Za-z0-9._-]+$")


if __name__ == "__main__":
    unittest.main()
