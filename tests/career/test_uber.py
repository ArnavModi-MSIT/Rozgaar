import unittest
from unittest.mock import patch

from backend.fetchers import uber


def page(number, ids, total=2, pages=2):
    return {'page': number, 'totalJobs': total, 'totalPages': pages, 'jobs': [{'Id': str(i), 'Title': 'Engineer', 'Description': '<p>Python</p>', 'Locations': [{'Address': 'Bengaluru, India'}], 'Urls': [{'Url': f'/en/jobs/{i}/', 'IsDefault': True}]} for i in ids]}


class UberTests(unittest.TestCase):
    def test_reads_all_pages_and_descriptions(self):
        with patch.object(uber, 'get_json', side_effect=[page(1, [1]), page(2, [2])]) as get, patch.object(uber.time, 'sleep'):
            result = uber.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['description'], 'Python')
        self.assertEqual(result[0]['url'], 'https://jobs.uber.com/en/jobs/1/')
        self.assertEqual(get.call_args.kwargs['params'], {'countries': 'India', 'page': 2})

    def test_later_failure_is_partial(self):
        with patch.object(uber, 'get_json', side_effect=[page(1, [1]), None]), patch.object(uber.time, 'sleep'):
            result = uber.collect()
        self.assertEqual(result.status, 'partial')
        self.assertIn('1 of 2', result.error)

    def test_first_failure_raises(self):
        with patch.object(uber, 'get_json', return_value=None):
            with self.assertRaises(RuntimeError):
                uber.collect()

    def test_valid_empty_search(self):
        with patch.object(uber, 'get_json', return_value=page(1, [], total=0, pages=0)):
            result = uber.collect()
        self.assertEqual(result.status, 'ok')
