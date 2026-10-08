import unittest
from unittest.mock import patch
from fetchers.standard import fetch_lever
class IonTests(unittest.TestCase):
    def test_country_and_complete_sections(self):
        india={'id':'i','country':'IN','text':'Analyst','categories':{'location':'Noida'},'hostedUrl':'https://jobs.lever.co/ion/i','description':'Intro','lists':[{'text':'Qualifications','content':'<p>3 years of experience</p>'}],'additional':'Closing'}
        foreign=dict(india,id='f',country='US')
        unknown=dict(india,id='u',country=None)
        with patch('fetchers.standard._get',return_value=[india,foreign,unknown]): jobs=fetch_lever('ion')
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['location'],'Noida, India')
        self.assertIn('3 years of experience',jobs[0]['description'])
        self.assertIn('Closing',jobs[0]['description'])
if __name__=='__main__': unittest.main()
