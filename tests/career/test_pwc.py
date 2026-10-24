import json,unittest
from unittest.mock import patch
from backend.fetchers import pwc
class PwcTests(unittest.TestCase):
    def test_invalid_listing_fails(self):
        with self.assertRaises(RuntimeError): pwc.listings('<html/>')
    def test_json_not_executed(self):
        self.assertEqual(pwc.listings('var jsondata = []; arbitrary();'),[])
    def test_detail_identity_country(self):
        d={'jobPostingInfo':{'jobReqId':'1','country':{'descriptor':'India'},'jobDescription':'<p>5 years of experience</p>'}}
        self.assertIn('5 years',pwc.detail(d,'1'))
        self.assertEqual(pwc.detail(d,'2'),'')
        d['jobPostingInfo']['country']['descriptor']='US'
        self.assertEqual(pwc.detail(d,'1'),'')
    def test_scope_and_missing_detail_partial(self):
        row=dict(jobreqid='1',title='Analyst',iso='IND',jobsite='Global_Experienced_Careers',location='Delhi',apply=pwc.ROOT+'/Global_Experienced_Careers/job/Delhi/Analyst_1/apply')
        foreign=dict(row,iso='USA',jobreqid='2')
        with patch.object(pwc,'get_text',return_value='var jsondata = '+json.dumps([row,foreign])),patch.object(pwc,'get_json',return_value=None): r=pwc.collect()
        self.assertEqual(len(r),1); self.assertEqual(r.status,'partial')
        self.assertEqual(r[0]['location'],'Delhi, India')
if __name__=='__main__': unittest.main()
