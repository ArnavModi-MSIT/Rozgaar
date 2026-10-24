import unittest
from unittest.mock import patch

import backend.config as config
from backend.fetchers import eightfold


class MicrosoftSearchTests(unittest.TestCase):
    def test_replacement_searches_send_filters_and_deduplicate(self):
        configs = [item for item in config.EIGHTFOLD if item['company'] == 'microsoft']
        calls = []
        def get(host, params):
            calls.append(params)
            return {'data': {'count': 1, 'positions': [{'id': '1', 'name': 'Engineer', 'locations': ['India']}]}}
        with patch.object(eightfold, '_get', side_effect=get):
            jobs = eightfold.collect(configs)
        self.assertEqual(len(jobs), 1)
        self.assertEqual({p['filter_seniority'] for p in calls}, {'Intern', 'Entry'})
        for params in calls:
            self.assertEqual(params['location'], 'India')
            self.assertEqual(params['filter_include_remote'], '1')
            self.assertEqual(params['filter_include_relocation'], '0')
            self.assertEqual(params['sort_by'], 'distance')
