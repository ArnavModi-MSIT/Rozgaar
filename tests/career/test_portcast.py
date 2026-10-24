import unittest
from unittest.mock import patch
from backend.fetchers import standard
from backend.core.location import is_india_or_unknown


class PortcastTests(unittest.TestCase):
    def test_foreign_primary_with_india_alternatives_is_retained(self):
        rows = [{'id': '1', 'text': 'Data Analyst Intern', 'hostedUrl': 'https://jobs.lever.co/portcast/1',
                 'categories': {'location': 'Singapore', 'allLocations': ['Singapore', 'Bangalore', 'Delhi', 'Bangalore']},
                 'lists': [{'text': 'Qualifications', 'content': '<p>Currently enrolled in a degree</p>'}]},
                {'id': '2', 'text': 'Sales Manager', 'hostedUrl': 'https://jobs.lever.co/portcast/2',
                 'categories': {'location': 'Mexico City', 'allLocations': ['Mexico City', 'Guadalajara']}}]
        with patch.object(standard, '_get', return_value=rows):
            result = standard.fetch_lever('portcast')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['location'], 'Bangalore, India; Delhi, India')
        self.assertTrue(is_india_or_unknown(result[0]['location']))
        self.assertIn('Currently enrolled', result[0]['description'])

    def test_primary_india_and_foreign_only_locations(self):
        self.assertEqual(standard._lever_location('portcast', {'categories': {'location': 'Delhi'}}), 'Delhi, India')
        self.assertEqual(standard._portcast_india_locations({'categories': {'location': 'Indianapolis'}}), [])
        self.assertEqual(standard._portcast_india_locations({'categories': {'location': 'Remote'}}), [])
