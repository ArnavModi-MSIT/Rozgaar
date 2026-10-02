import unittest
from unittest.mock import patch

from fetchers import barclays


def page(number, ids, total=3, pages=2):
    cards = ''.join(f'<div><a data-job-id="{i}" href="/job/{i}">Engineer {i}</a><div class="job-location">Pune, India</div></div>' for i in ids)
    return f'<div id="search-results" data-current-page="{number}" data-total-results="{total}" data-total-pages="{pages}"><section id="search-results-list">{cards}</section></div>'


class BarclaysTests(unittest.TestCase):
    def test_pages_and_descriptions(self):
        def get(url):
            if url == barclays.SEARCH_URL:
                return page(1, [1, 2])
            if url.endswith('?p=2'):
                return page(2, [2, 3])
            return '<div class="ats-description">Python and SQL</div>'
        with patch.object(barclays, '_get', side_effect=get):
            result = barclays.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['location'], 'Pune, India')
        self.assertEqual(result[0]['description'], 'Python and SQL')

    def test_repeated_page_is_partial(self):
        with patch.object(barclays, '_get', return_value=page(1, [1])), patch.object(barclays, '_description', return_value='SQL'):
            result = barclays.collect()
        self.assertEqual(result.status, 'partial')
        self.assertIn('1 of 3', result.error)

    def test_failed_first_page_raises(self):
        with patch.object(barclays, '_get', return_value=None):
            with self.assertRaises(RuntimeError):
                barclays.collect()

    def test_valid_empty_search(self):
        with patch.object(barclays, '_get', return_value=page(1, [], total=0, pages=0)):
            result = barclays.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result), 0)
