import unittest
from unittest.mock import patch

from fetchers import amazon


def job(i):
    return {'id_icims': i, 'title': 'Engineer', 'job_path': f'/jobs/{i}', 'description': 'SQL', 'normalized_location': 'India'}


class AmazonTests(unittest.TestCase):
    def test_reads_beyond_old_ten_page_limit(self):
        offsets = []
        def get(url, params):
            offsets.append(params['offset'])
            self.assertNotIn('base_query', params)
            start = params['offset']
            return {'hits': 551, 'jobs': [job(i) for i in range(start, min(start + 50, 551))]}
        with patch.object(amazon, '_get', side_effect=get), patch.object(amazon.time, 'sleep'):
            result = amazon.fetch_query({'industry_experience': 'less_than_1_year'})
        self.assertEqual(len(result), 551)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(offsets[-1], 550)

    def test_failed_later_page_is_partial(self):
        with patch.object(amazon, '_get', side_effect=[{'hits': 2, 'jobs': [job(1)]}, None]), patch.object(amazon.time, 'sleep'):
            result = amazon.fetch_query({})
        self.assertEqual(result.status, 'partial')
        self.assertIn('1 of 2', result.error)

    def test_failed_first_page_raises(self):
        with patch.object(amazon, '_get', return_value=None):
            with self.assertRaises(RuntimeError):
                amazon.fetch_query({})

    def test_complete_empty_search(self):
        with patch.object(amazon, '_get', return_value={'hits': 0, 'jobs': []}):
            result = amazon.fetch_query({})
        self.assertEqual(result.status, 'ok')

    def test_repeat_is_partial(self):
        with patch.object(amazon, '_get', return_value={'hits': 2, 'jobs': [job(1)]}), patch.object(amazon.time, 'sleep'):
            result = amazon.fetch_query({})
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result), 1)
