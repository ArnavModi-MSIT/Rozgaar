import unittest

from backend.config import career_browser_20261102 as batch
from backend.config import sources


class BrowserSourceTests(unittest.TestCase):
    def test_rows_are_registered_with_expected_shapes(self):
        by_key = {row["key"]: row for row in batch.SOURCES}
        self.assertEqual(set(by_key), {"ice", "cmegroup", "nomura", "synopsys", "moodys", "aon", "marsh", "genpact", "macquarie", "kpmg", "hexaware", "vodafoneidea",
                                "capgemini", "leadsquared", "delhivery", "schneiderelectric", "eaton", "bp", "cummins", "ey", "wipro", "hcltech", "urbancompany", "mckinsey"})
        self.assertIn({"company": "ice", "kind": "jibe", "host": "careers.ice.com", "client_code": "ice"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "cmegroup", "tenant": "cmegroup", "wd_server": "wd1", "site": "cme_careers",
                       "verify_detail_country": True}, sources.WORKDAY_INDIA)
        self.assertIn({"company": "nomura", "host": "careers.nomura.com", "fetch_details": True}, sources.SUCCESSFACTORS)
        self_cfg = {"company": "synopsys", "kind": "talentbrew", "host": "careers.synopsys.com", "org_id": 44408}
        self.assertIn(self_cfg, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "moodys", "kind": "talentbrew", "host": "careers.moodys.com", "org_id": 49841}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "macquarie", "kind": "avature", "host": "recruitment.macquarie.com", "path": "/en_US/careers",
                       "query": "10671=%5B871433%5D&10671_format=21337&listFilterMode=1"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "kpmg", "kind": "oracle", "base_url": "https://ejgk.fa.em2.oraclecloud.com", "site": "CX_3"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "hexaware", "kind": "oracle", "base_url": "https://fa-etqo-saasfaprod1.fa.ocs.oraclecloud.com",
                       "site": "CX_1"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "vodafoneidea", "host": "careers.vodafoneidea.com", "fetch_details": True}, sources.SUCCESSFACTORS)
        self.assertIn({"company": "capgemini", "kind": "capgemini"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "leadsquared", "kind": "darwinbox", "host": "leadsquaredhrms.darwinbox.in"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "delhivery", "kind": "darwinbox", "host": "delhivery.darwinbox.in"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "schneiderelectric", "kind": "jibe", "host": "careers.se.com"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "cummins", "kind": "oracle", "base_url": "https://fa-espx-saasfaprod1.fa.ocs.oraclecloud.com",
                       "site": "CX_1"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "eaton", "host": "eaton.eightfold.ai", "domain": "eaton.com", "location": "India",
                       "fetch_details": True}, sources.EIGHTFOLD)
        self.assertIn({"company": "bp", "tenant": "bpinternational", "wd_server": "wd3", "site": "bpCareers",
                       "verify_detail_country": True}, sources.WORKDAY_INDIA)
        self.assertIn({"company": "ey", "host": "careers.ey.com", "path": "/ey/search/", "extra_query": "locationsearch=India",
                       "country_scoped": "India", "fetch_details": True}, sources.SUCCESSFACTORS)
        self.assertIn({"company": "wipro", "host": "careers.wipro.com", "variant": "rmk", "category_id": 0,
                       "facet_filters": {"jobLocationCountry": ["India"]}, "location_style": "city_country",
                       "fetch_details": True}, sources.SUCCESSFACTORS)
        self.assertIn({"company": "hcltech", "host": "careers.hcltech.com", "variant": "rmk", "category_id": 0,
                       "facet_filters": {"custCountryRegion": ["India"]}, "fetch_details": True}, sources.SUCCESSFACTORS)
        self.assertIn({"company": "urbancompany", "kind": "urbancompany"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "mckinsey", "kind": "mckinsey"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "aon", "kind": "jibe", "host": "jobs.aon.com"}, sources.EMPLOYER_PORTALS)
        self.assertIn({"company": "marsh", "domain": "careers.marsh.com", "refnum": "MAMCGLOBAL", "locale": "global/en"}, sources.PHENOM)
        self.assertIn({"company": "genpact", "tenant": "genpact", "wd_server": "wd108", "site": "External_Careers",
                       "verify_detail_country": True}, sources.WORKDAY_INDIA)
        for key, row in by_key.items():
            self.assertEqual(sources.DISPLAY_NAMES[key], row["name"])
            self.assertTrue(row["career_url"].startswith("https://"))

    def test_keys_do_not_collide_with_other_sources(self):
        keys = [row["key"] for row in batch.SOURCES]
        for group in (sources.GREENHOUSE, sources.LEVER, sources.ASHBY):
            self.assertFalse({k.lower() for k in keys} & {str(x).lower() for x in group})
        for name in ("EMPLOYER_PORTALS", "WORKDAY_INDIA", "SUCCESSFACTORS", "PHENOM", "EIGHTFOLD"):
            companies = [item["company"] for item in getattr(sources, name)]
            for key in keys:
                self.assertLessEqual(companies.count(key), 1, (name, key))


if __name__ == "__main__":
    unittest.main()
