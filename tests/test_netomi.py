import unittest
from unittest.mock import patch

import config
from fetchers import standard


class NetomiTests(unittest.TestCase):
    def test_requested_locations_and_qualification_lists(self):
        rows = [{'id': str(i), 'text': 'Data Engineer I', 'hostedUrl': f'https://jobs.lever.co/netomi/{i}',
                 'categories': {'location': location}, 'description': '<p>Data platform</p>',
                 'lists': [{'text': 'Qualifications', 'content': '<p>1 year experience with SQL</p>'}]}
                for i, location in enumerate(['Remote - India', 'Gurugram', 'Remote', 'New York', 'United States (Remote)'])]
        with patch.object(standard, '_get', return_value=rows):
            jobs = standard.fetch_lever('netomi')
        self.assertIn('netomi', config.LEVER)
        self.assertEqual(len(jobs), 2)
        self.assertEqual({j['location'] for j in jobs}, {'Remote - India', 'Gurugram, India'})
        self.assertTrue(all('1 year experience with SQL' in j['description'] for j in jobs))

    def test_valid_empty_and_failed_board_are_distinct(self):
        with patch.object(standard, '_get', return_value=[]):
            self.assertEqual(standard.fetch_lever('netomi'), [])
        with patch.object(standard, '_get', return_value=None):
            with self.assertRaises(RuntimeError):
                standard.fetch_lever('netomi')
