import unittest
from unittest.mock import patch
from fetchers import makemytrip as m
from core.experience import extract_min_experience

def detail(sid='one',desc='&lt;p&gt;SQL analytics&lt;/p&gt;'):
    return {'status':1,'data':{'applyUrl':'https://gommt.darwinbox.in/ms/candidatev2/main/careers/jobDetails/'+sid,'job_decription':desc,'experience_from':'2','experience_to':'5','unit_experience':'Years'}}

class MakeMyTripTests(unittest.TestCase):
    def test_encoded_description_and_stronger_requirement_survive(self):
        desc='&lt;p&gt;Background&lt;/p&gt;'*1000+'&lt;h2&gt;Requirements&lt;/h2&gt;&lt;p&gt;7 years of experience&lt;/p&gt;'
        parsed=m.parse_detail(detail(desc=desc),'one')
        self.assertIn('2-5 years',parsed)
        self.assertIn('7 years of experience',parsed)
        self.assertEqual(extract_min_experience(parsed),7)

    def test_detail_for_wrong_id_is_rejected(self):
        self.assertEqual(m.parse_detail(detail('other'),'one'),'')

    def test_months_are_converted_to_years(self):
        response=detail();response['data'].update(unit_experience='Months',experience_from='18',experience_to='30')
        self.assertIn('1.5-2.5 years',m.parse_detail(response,'one'))

    def test_blocked_listing_is_not_valid_zero(self):
        with patch.object(m,'get_json',return_value=None):
            with self.assertRaises(RuntimeError):m.collect()

    def test_whole_list_and_india_gate(self):
        listings=[dict(job_id='one',job_title='Analyst',location_country='India',location=['Gurgaon, India']),dict(job_id='two',job_title='Engineer',location_country='Singapore',location=['Singapore'])]
        with patch.object(m,'get_json',side_effect=[{'allJobs':listings},detail()]):
            jobs=m.collect()
        self.assertEqual(jobs.status,'ok')
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['url'],'https://careers.makemytrip.com/prod/opportunity/one/analyst')

    def test_missing_detail_reports_partial(self):
        listings=[dict(job_id='one',job_title='Analyst',location_country='India',location=['Gurgaon, India'])]
        with patch.object(m,'get_json',side_effect=[{'allJobs':listings},None]):jobs=m.collect()
        self.assertEqual(jobs.status,'partial')
        self.assertEqual(jobs[0]['description'],'')

if __name__=='__main__':unittest.main()
