import unittest
import config
from fetchers.smartrecruiters import _format_location
from core.location import parse_country

class PhonePeTests(unittest.TestCase):
    def test_configured(self):
        self.assertIn("PHONEPELIMITED", [c["company_id"] for c in config.SMARTRECRUITERS])

    def test_india_iso_location(self):
        location = _format_location({"city": "Bengaluru", "region": "Karnataka", "country": "in"})
        self.assertEqual(parse_country(location), "India")
