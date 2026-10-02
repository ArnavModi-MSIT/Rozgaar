import unittest
from unittest.mock import patch

from fetchers import flipkart


JOB = {'JobId': '1', 'JobTitle': 'Engineer', 'Location': '[{"Address":"Bengaluru, India"}]', 'Experience': {'MinExp': 0}, 'Skills': ['Python'], 'JobDescriptionV2': '<p>Build software</p>'}


class FlipkartTests(unittest.TestCase):
    def test_full_feed_and_description(self):
        with patch.object(flipkart, 'get_json', side_effect=[{'access_token': 'fixture'}, JOB]), patch.object(flipkart, 'post_json', return_value={'Total': 1, 'Result': [JOB]}):
            result = flipkart.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result[0]['location'], 'Bengaluru, India')
        self.assertIn('Minimum experience required: 0 years.', result[0]['description'])
        self.assertEqual(result[0]['url'], 'https://flipkart.turbohire.co/job/publicjobs/1')

    def test_truncated_feed_is_partial(self):
        with patch.object(flipkart, 'get_json', side_effect=[{'access_token': 'fixture'}, JOB]), patch.object(flipkart, 'post_json', return_value={'Total': 2, 'Result': [JOB]}):
            result = flipkart.collect()
        self.assertEqual(result.status, 'partial')
        self.assertIn('1 of 2', result.error)

    def test_access_failure_is_not_empty_success(self):
        with patch.object(flipkart, 'get_json', return_value=None):
            with self.assertRaises(RuntimeError):
                flipkart.collect()

    def test_valid_empty_feed(self):
        with patch.object(flipkart, 'get_json', return_value={'access_token': 'fixture'}), patch.object(flipkart, 'post_json', return_value={'Total': 0, 'Result': []}):
            result = flipkart.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result), 0)
