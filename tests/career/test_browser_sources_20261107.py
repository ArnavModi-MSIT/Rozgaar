import re
import unittest

from backend.config import career_browser_20261107 as batch
from backend.config import sources

EXPECTED = {
    "cigna": "cigna", "mufg": "mufgub", "ameriprise": "ameriprise", "wolterskluwer": "wk", "sabre": "sabre",
    "genesys": "genesys", "clarivate": "clarivate", "invesco": "invesco", "trellix": "trellix",
    "prudential": "prudential", "fico": "fico", "finastra": "finastra", "globalpayments": "tsys",
    "vanguard": "vanguard", "danaher": "danaher", "threem": "3m", "novartis": "novartis", "gsk": "gsk",
    "philips": "philips", "rockwell": "rockwellautomation",
}


class WorkdayBatchTests(unittest.TestCase):
    def test_twenty_rows_with_expected_tenants(self):
        self.assertEqual({r["key"]: r["config"]["tenant"] for r in batch.SOURCES}, EXPECTED)

    def test_rows_are_registered_once_in_workday_india(self):
        by_company = [c["company"] for c in sources.WORKDAY_INDIA]
        for key in EXPECTED:
            self.assertEqual(by_company.count(key), 1, key)
            self.assertIn(key, sources.DISPLAY_NAMES)

    def test_rows_use_detail_country_check_and_valid_patterns(self):
        for row in batch.SOURCES:
            cfg = row["config"]
            self.assertEqual(row["group"], "workday_india")
            self.assertTrue(cfg["verify_detail_country"], row["key"])
            self.assertRegex(cfg["wd_server"], r"^wd\d+$")
            if "india_facet_pattern" in cfg:
                re.compile(cfg["india_facet_pattern"])
            self.assertIn(cfg["tenant"], row["career_url"])

    def test_no_key_collides_with_earlier_batches(self):
        from backend.config import career_browser_20261102 as earlier
        self.assertFalse({r["key"] for r in batch.SOURCES} & {r["key"] for r in earlier.SOURCES})


if __name__ == "__main__":
    unittest.main()
