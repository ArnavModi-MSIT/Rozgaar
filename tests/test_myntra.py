import unittest
from unittest.mock import patch
from fetchers import myntra
from core.experience import extract_min_experience

def row(sid='1',description='<p>SQL analytics</p>'):
    return dict(displayId=sid,workspaceId='MYNTRA-test',jobTitle='Analyst',jobDescription=description,jobLocation=[dict(city='Bangalore',state='Karnataka',country='India')],requiredExperienceInMonths={'from':24,'to':48})

class MyntraTests(unittest.TestCase):
    def test_pagination_collects_all_unique_jobs(self):
        with patch.object(myntra,'get_text',return_value='MYNTRA-test'), patch.object(myntra,'get_json',side_effect=[{'total':2,'entities':[row('1')]},{'total':2,'entities':[row('2')]}]) as get, patch.object(myntra.time,'sleep'):
            jobs=myntra.collect()
        self.assertEqual(jobs.status,'ok')
        self.assertEqual(len(jobs),2)
        self.assertEqual([call.kwargs['params']['page'] for call in get.call_args_list],[1,2])
        self.assertEqual(jobs[0]['url'],'https://jobs.myntra.com/jobs/1')

    def test_metadata_months_and_late_description_requirements_are_preserved(self):
        job=row(description='<p>Background</p>'*1000+'<h2>Requirements</h2><p>5+ years of experience</p>')
        parsed=myntra.parse_job(job)
        self.assertIn('2-4 years of professional experience',parsed['description'])
        self.assertIn('5+ years of experience',parsed['description'])
        self.assertEqual(extract_min_experience(parsed['description']),5)

    def test_foreign_location_is_excluded(self):
        job=row();job['jobLocation']=[dict(city='Indianapolis',state='IN',country='US')]
        self.assertIsNone(myntra.parse_job(job))

    def test_empty_description_stays_partial_despite_metadata(self):
        with patch.object(myntra,'get_text',return_value='MYNTRA-test'),patch.object(myntra,'get_json',return_value={'total':1,'entities':[row(description='')]}):
            jobs=myntra.collect()
        self.assertEqual(jobs.status,'partial')
        self.assertEqual(jobs[0]['description'],'')

    def test_wrong_workspace_is_not_successful_zero(self):
        job=row();job['workspaceId']='OTHER-company'
        with patch.object(myntra,'get_text',return_value='MYNTRA-test'),patch.object(myntra,'get_json',return_value={'total':1,'entities':[job]}):
            with self.assertRaisesRegex(RuntimeError,'unexpected workspace'):myntra.collect()

    def test_repeated_page_reports_partial(self):
        with patch.object(myntra,'get_text',return_value='MYNTRA-test'),patch.object(myntra,'get_json',return_value={'total':2,'entities':[row()]}),patch.object(myntra.time,'sleep'):
            jobs=myntra.collect()
        self.assertEqual(jobs.status,'partial')
        self.assertEqual(len(jobs),1)

if __name__=='__main__':unittest.main()
