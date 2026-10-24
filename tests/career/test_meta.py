import unittest
from unittest.mock import patch

from backend.fetchers import meta


ROW = {'id': '1', 'title': 'Engineer', 'locations': ['Bangalore, India']}


class MetaTests(unittest.TestCase):
    def collect_fixture(self, count):
        responses = [{'job_search_with_featured_jobs_v2': {'all_jobs': [ROW], 'featured_jobs': [{'id': 'foreign', 'title': 'Other', 'locations': ['United States']}]}}, {'job_search_with_featured_jobs_v2': {'job_count': count}}]
        with patch.object(meta, '_bootstrap', return_value=('fixture', {meta.RESULT_QUERY: '1', meta.COUNT_QUERY: '2'})), patch.object(meta, '_query', side_effect=responses) as query, patch.object(meta, '_description', return_value='Python required'):
            result = meta.collect()
        self.assertEqual(query.call_args_list[0].args[3]['search_input']['offices'], meta.OFFICES)
        self.assertFalse(query.call_args_list[0].args[3]['isLoggedIn'])
        return result

    def test_all_offices_and_excludes_featured_recommendations(self):
        result = self.collect_fixture(1)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['description'], 'Python required')

    def test_missing_results_are_partial(self):
        result = self.collect_fixture(2)
        self.assertEqual(result.status, 'partial')
        self.assertIn('1 of 2', result.error)

    def test_missing_operation_fails(self):
        with patch.object(meta, '_bootstrap', side_effect=RuntimeError('operation unavailable')):
            with self.assertRaises(RuntimeError):
                meta.collect()
