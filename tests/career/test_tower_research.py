import unittest
from unittest.mock import patch
from backend.core.location import parse_country
from backend.fetchers import tower_research as tower

class TowerTests(unittest.TestCase):
    def test_locations(self):
        for location in ("Gurgaon", "Gift City", "Singapore, Hong Kong, Gurgaon"):
            self.assertEqual(parse_country(tower.normalize_location(location)), "India")
        self.assertEqual(parse_country(tower.normalize_location("London")), "United Kingdom")
        self.assertEqual(tower.normalize_location("Multiple Locations"), "Multiple Locations")

    def test_empty_board(self):
        with patch.object(tower, "fetch_greenhouse", return_value=[]):
            self.assertEqual(tower.collect().status, "ok")
