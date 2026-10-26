import unittest
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from unittest.mock import patch
import requests

from backend.fetchers import eightfold, expedia, qualcomm_students
from backend.fetchers.http_client import retry_after_delay


def response(status=200, headers=None, payload=None):
    r=requests.Response();r.status_code=status;r.headers.update(headers or {});r._content=b'<html>jobs</html>';r.json=lambda: payload or {'data':{'positions':[],'count':0}}
    return r

class ListingRetryTests(unittest.TestCase):
    def test_retry_after_seconds_date_and_invalid(self):
        self.assertEqual(retry_after_delay('5',1),5)
        future=format_datetime(datetime.now(timezone.utc)+timedelta(seconds=20),usegmt=True)
        self.assertTrue(18 < retry_after_delay(future,1) <= 20)
        for text in ['bad','inf','nan',None]:self.assertEqual(retry_after_delay(text,2),2)

    def test_expedia_recovers_after_rate_limit(self):
        with patch.object(expedia.SESSION,'get',side_effect=[response(429,{'Retry-After':'3'}),response()]) as get,patch.object(expedia.time,'sleep') as sleep:
            self.assertEqual(expedia._get(1),'<html>jobs</html>')
        self.assertEqual(get.call_count,2);sleep.assert_called_once_with(3)

    def test_expedia_long_rate_limit_is_not_retried_early(self):
        with patch.object(expedia.SESSION,'get',return_value=response(429,{'Retry-After':'120'})) as get,patch.object(expedia.time,'sleep') as sleep:
            with self.assertRaisesRegex(expedia.ListingUnavailable,'retry after 120'):expedia._get(1)
        get.assert_called_once();sleep.assert_not_called()

    def test_expedia_repeated_rate_limit_is_bounded(self):
        with patch.object(expedia.SESSION,'get',return_value=response(429)) as get,patch.object(expedia.time,'sleep'):
            with self.assertRaisesRegex(expedia.ListingUnavailable,'HTTP 429'):expedia._get(1)
        self.assertEqual(get.call_count,3)

    def test_eightfold_recovers_after_rate_limit(self):
        with patch.object(eightfold.SESSION,'get',side_effect=[response(429,{'Retry-After':'2'}),response()]),patch.object(eightfold.time,'sleep') as sleep:
            self.assertEqual(eightfold._get('example.com',{})['data']['count'],0)
        sleep.assert_called_once_with(2)

    def test_eightfold_rejection_is_explicit_and_not_retried(self):
        with patch.object(eightfold.SESSION,'get',return_value=response(403)) as get:
            with self.assertRaisesRegex(eightfold.ListingUnavailable,'HTTP 403'):eightfold._get('example.com',{})
        get.assert_called_once()

    def test_eightfold_transport_failure_has_bounded_retries(self):
        with patch.object(eightfold.SESSION,'get',side_effect=requests.Timeout) as get,patch.object(eightfold.time,'sleep'):
            with self.assertRaisesRegex(eightfold.ListingUnavailable,'Timeout'):eightfold._get('example.com',{})
        self.assertEqual(get.call_count,3)

    def test_qualcomm_retains_previous_page_on_rejection(self):
        rows=[dict(id=i,name='Intern',locations=['Hyderabad, India']) for i in range(1,11)]
        with patch.object(eightfold,'_get',side_effect=[{'data':{'count':11,'positions':rows}},eightfold.ListingUnavailable('HTTP 403')]),patch.object(qualcomm_students,'_description',return_value='Full description'),patch.object(qualcomm_students.time,'sleep'):
            result=qualcomm_students.collect()
        self.assertEqual(result.status,'partial');self.assertEqual(len(result),10);self.assertIn('HTTP 403',result.error)
        with patch.object(eightfold,'_get',side_effect=eightfold.ListingUnavailable('HTTP 403')):
            with self.assertRaisesRegex(RuntimeError,'offset 0.*HTTP 403'):qualcomm_students.collect()
