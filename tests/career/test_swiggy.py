import unittest
from unittest.mock import patch
from backend.fetchers import swiggy

ROW = {"t":"Data Analyst", "c":"Bengaluru", "l":"Bengaluru, India", "u":"https://jobs.smartrecruiters.com/SWIGGY/600000001-data-analyst?trid=tracking"}

class SwiggyTests(unittest.TestCase):
    def test_current_feed_dedup_and_full_description(self):
        text = 'Python SQL responsibilities. ' * 500 + 'Final qualification: 5 years.'
        with patch.object(swiggy, 'get_json', return_value={'total':2,'jobs':[ROW,ROW]}) as get, patch.object(swiggy, 'fetch_posting_description', return_value=text) as detail:
            result = swiggy.collect()
        self.assertEqual(len(result),1)
        self.assertEqual(result.status,'ok')
        self.assertEqual(result[0]['source_id'],'600000001')
        self.assertEqual(result[0]['url'],'https://jobs.smartrecruiters.com/SWIGGY/600000001-data-analyst')
        self.assertTrue(result[0]['description'].endswith('Final qualification: 5 years.'))
        self.assertGreater(len(result[0]['description']),10000)
        detail.assert_called_once_with('SWIGGY','600000001')
        self.assertEqual(get.call_args.args[1],'https://careers.swiggy.com/api/jobs.json')

    def test_empty_and_failed(self):
        with patch.object(swiggy,'get_json',return_value={'total':0,'jobs':[]}):
            self.assertEqual(swiggy.collect().status,'ok')
        for data in [None,{'jobs':[]},{'reqDetailsBOList':[]}]:
            with patch.object(swiggy,'get_json',return_value=data), self.assertRaises(RuntimeError):
                swiggy.collect()

    def test_missing_description_preserves_listing_as_partial(self):
        with patch.object(swiggy,'get_json',return_value={'total':1,'jobs':[ROW]}), patch.object(swiggy,'fetch_posting_description',return_value=''):
            result=swiggy.collect()
        self.assertEqual(len(result),1)
        self.assertEqual(result.status,'partial')

    def test_malformed_rows_do_not_discard_valid_jobs(self):
        bad=dict(ROW,u='https://jobs.smartrecruiters.com/OTHER/600000002-wrong-company')
        with patch.object(swiggy,'get_json',return_value={'total':2,'jobs':[ROW,bad]}), patch.object(swiggy,'fetch_posting_description',return_value='Full description'):
            result=swiggy.collect()
        self.assertEqual(len(result),1)
        self.assertEqual(result.status,'partial')
        self.assertIn('malformed',result.error)

    def test_incomplete_feed_count_is_partial(self):
        with patch.object(swiggy,'get_json',return_value={'total':2,'jobs':[ROW]}), patch.object(swiggy,'fetch_posting_description',return_value='Full description'):
            self.assertIn('1 of 2',swiggy.collect().error)
