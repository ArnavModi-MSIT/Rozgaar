import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.fetchers import hrt


class HrtTests(unittest.TestCase):
    def test_http_rejection_explains_actual_status(self):
        def unavailable(session, url):
            for hook in session.hooks['response']:
                hook(SimpleNamespace(status_code=403))
            return None
        with patch.object(hrt, 'get_text', side_effect=unavailable), patch.object(hrt, 'post_json') as post:
            with self.assertRaisesRegex(RuntimeError, r'HTTP 403.*no listings fetched'):
                hrt.collect()
        post.assert_not_called()

    def test_challenge_html_is_not_treated_as_empty_success(self):
        with patch.object(hrt, 'get_text', return_value='<title>Just a moment...</title>'):
            with self.assertRaisesRegex(RuntimeError, 'access challenge'):
                hrt.collect()

    def test_layout_change_is_distinct_from_blocked_request(self):
        with patch.object(hrt, 'get_text', return_value='<title>Careers</title><p>New layout</p>'):
            with self.assertRaisesRegex(RuntimeError, 'careers settings unavailable'):
                hrt.collect()

    def test_valid_empty_response_still_successful(self):
        html='<div class="hrt-card-wrapper" data-filters-settings="{}"></div>'
        with patch.object(hrt, 'get_text', return_value=html), patch.object(hrt, 'post_json', return_value=[]):
            result=hrt.collect()
        self.assertEqual(result.status,'ok');self.assertEqual(len(result),0)

    def test_expired_deadline_does_not_request(self):
        with patch.object(hrt, 'get_text') as get:
            self.assertEqual(hrt.collect(time.monotonic()-1).status,'partial')
        get.assert_not_called()
