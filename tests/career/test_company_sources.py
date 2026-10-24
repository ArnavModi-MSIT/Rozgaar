import json
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.fetchers import workday_india, zerodha, automattic, swiggy, bloomberg

class CompanySourceTests(unittest.TestCase):
    def test_manifest_has_exactly_75_unique_companies(self):
        from rozgaar.paths import ROOT
        rows=json.loads((ROOT/"docs/catalog/COMPANY_SOURCES.json").read_text())
        self.assertEqual(len(rows),75)
        self.assertEqual(len({r["key"] for r in rows}),75)

    def test_workday_prefers_country_and_excludes_indiana(self):
        data={"facets":[{"facetParameter":"locations","values":[{"id":"us","descriptor":"Indiana"},{"id":"in-city","descriptor":"IND-Bangalore"}]},{"facetParameter":"locationCountry","values":[{"id":"in","descriptor":"India"}]}]}
        self.assertEqual(workday_india._facets(data),{"locationCountry":["in"]})

    def test_workday_nested_location_facets(self):
        data={"facets":[{"values":[{"facetParameter":"locations","values":[{"id":"in","descriptor":"IND-Bangalore"}]}]}]}
        self.assertEqual(workday_india._facets(data),{"locations":["in"]})

    def test_workday_missing_india_is_not_empty_success(self):
        with self.assertRaises(RuntimeError):workday_india._facets({"facets":[]})

    def test_zerodha_verified_empty(self):
        with patch.object(zerodha,"get_json",return_value={"success":True,"data":[]}):
            result=zerodha.collect()
        self.assertEqual(result.status,"ok")
        self.assertEqual(len(result),0)

    def test_zerodha_bad_response_is_failure(self):
        with patch.object(zerodha,"get_json",return_value=None):
            with self.assertRaises(RuntimeError):zerodha.collect()

    def test_remote_jobs_do_not_claim_india_eligibility(self):
        html='const ghJobsData = '+json.dumps([{"id":1,"title":"Engineer","href":"https://automattic.com/job/1","content":"Remote"}])+';'
        with patch.object(automattic,"get_text",return_value=html):result=automattic.collect()
        self.assertEqual(result.status,"partial")
        self.assertNotIn("India",result[0]["location"])

    def test_swiggy_normalizes_known_city_only(self):
        self.assertEqual(swiggy.normalize_location("Bengaluru"),"Bengaluru, India")
        self.assertEqual(swiggy.normalize_location("New York"),"New York")

    def test_bloomberg_rejects_missing_total(self):
        with self.assertRaises(RuntimeError):bloomberg._page("<html>Unavailable</html>")
