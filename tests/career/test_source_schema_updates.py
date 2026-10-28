import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.fetchers import zerodha, expedia


class SourceSchemaUpdatesTests(unittest.TestCase):
    def test_expedia_india_query_and_client_scope(self):
        with patch.object(expedia.SESSION,'get',return_value=SimpleNamespace(status_code=200,text='HTML',raise_for_status=lambda:None)) as get:
            self.assertEqual(expedia._get(2),'HTML')
        self.assertEqual(get.call_args.kwargs['params'],{'mypage':2,'filter[country]':'India'})
        def card(id,location):
            return '<li class="Results__list__item"><a class="view-job-button" href="/job/R-'+id+'/"></a><h3 class="Results__list__title">Engineer</h3><h4 class="Results__list__location">'+location+'</h4></li>'
        with patch.object(expedia,'_get',side_effect=[card('1','India - Bangalore')+card('2','United States - Indiana'),'<div></div>']),patch.object(expedia.time,'sleep'):
            result=expedia.collect()
        self.assertEqual([j['source_id'] for j in result],['R-1'])

    def test_zerodha_slug_and_nullable_location_retain_full_description(self):
        text = 'Video editing responsibilities. ' * 500 + 'Final qualification.'
        row = {'name':'video-editor','job_title':'Video Editor','location':None,'description':text}
        with patch.object(zerodha,'get_json',return_value={'success':True,'count':1,'data':[row]}):
            result = zerodha.collect()
        self.assertEqual(result.status,'ok')
        self.assertEqual(result[0]['source_id'],'video-editor')
        self.assertEqual(result[0]['location'],'')
        self.assertEqual(result[0]['description'],text)

    def test_zerodha_mixed_rows_preserve_valid_listings(self):
        row = {'name':'analyst','job_title':'Analyst','description':'Full description'}
        with patch.object(zerodha,'get_json',return_value={'success':True,'data':[{},row]}):
            result = zerodha.collect()
        self.assertEqual(len(result),1)
        self.assertEqual(result.status,'partial')
        with patch.object(zerodha,'get_json',return_value={'success':True,'data':[{}]}), self.assertRaises(RuntimeError):
            zerodha.collect()

    def test_expedia_403_is_reported_without_retrying_rejection(self):
        with patch.object(expedia.SESSION,'get',return_value=SimpleNamespace(status_code=403)) as get:
            with self.assertRaisesRegex(RuntimeError,'HTTP 403'):
                expedia.collect()
        get.assert_called_once()

    def test_expedia_challenge_is_not_empty_success(self):
        with patch.object(expedia,'_get',return_value='<title>Attention Required! | Cloudflare</title>'):
            with self.assertRaisesRegex(RuntimeError,'access challenge'):
                expedia.collect()

    def test_expedia_later_rejection_preserves_previous_page(self):
        html = '<li class="Results__list__item"><a class="view-job-button" href="/jobs/R-1/"></a><h3 class="Results__list__title">Engineer</h3><h4 class="Results__list__location">India</h4></li>'
        with patch.object(expedia,'_get',side_effect=[html,expedia.ListingUnavailable('HTTP 403')]), patch.object(expedia.time,'sleep'):
            result=expedia.collect()
        self.assertEqual(len(result),1)
        self.assertEqual(result.status,'partial')
        self.assertIn('HTTP 403',result.error)
