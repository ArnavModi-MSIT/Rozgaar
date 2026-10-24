import json
import unittest
from unittest.mock import patch

from backend.core.description_quality import annotate_jobs, description_quality
from backend.fetchers import eightfold
from scripts.career.repair_export import repair_job


class DescriptionQualityTests(unittest.TestCase):
    def test_insufficient_text_never_implies_rejection_or_eligibility(self):
        jobs = [{'id':'a', 'description':''}, {'id':'b','description':'Department: Risk / Policy Mgmt'},
                {'id':'c','description':"Innovate in Bengaluru This office offers perks to enhance your work experience. Lowe's is an equal opportunity employer."}]
        summary = annotate_jobs(jobs)
        self.assertEqual(summary['missing_or_insufficient'], 3)
        self.assertTrue(all(j['assessment_status'] == 'unable_to_assess' for j in jobs))

    def test_shared_text_preserves_distinct_requisitions(self):
        text = 'Responsibilities include designing data pipelines and maintaining analytics systems. ' * 4
        jobs = [{'id':'a','description':text}, {'id':'b','description':'  '+text.replace(' ', '  ')}]
        annotate_jobs(jobs)
        self.assertEqual([j['id'] for j in jobs], ['a','b'])
        self.assertEqual(jobs[0]['description_group'], jobs[1]['description_group'])
        self.assertEqual(jobs[0]['same_description_count'], 2)
        self.assertEqual(jobs[0]['assessment_status'], 'requires_review')

    def test_office_intro_does_not_hide_following_real_role(self):
        self.assertEqual(description_quality('Innovate in Bengaluru Responsibilities: develop data pipelines. ' * 10), 'available')
        self.assertEqual(description_quality('Department: Engineering\nResponsibilities: develop data pipelines. ' * 10), 'available')
        self.assertEqual(description_quality('Department: Engineering\nResponsibilities: develop data pipelines.'), 'needs_review')

    def test_eightfold_rejects_wrong_job_and_accepts_matching_public_data(self):
        job = {'url':'https://jobs.ericsson.com/careers/job/123','title':'Data Analyst'}
        row = {'@type':'JobPosting','url':job['url'],'title':job['title'],'description':'<p>Actual role</p>'}
        with patch.object(eightfold, 'get_text', return_value='<script type="application/ld+json">'+json.dumps(row)+'</script>'):
            self.assertEqual(eightfold.fetch_description(job), 'Actual role')
        row['url'] = 'https://jobs.ericsson.com/careers/job/999'
        with patch.object(eightfold, 'get_text', return_value='<script type="application/ld+json">'+json.dumps(row)+'</script>'):
            self.assertEqual(eightfold.fetch_description(job), '')

    def test_failed_repair_retains_original_text_and_scores(self):
        job = {'id':'example:1','description':'Department: Engineering','resume_match_pct':20}
        with patch('scripts.career.repair_export.retrieve', return_value=('', {'result':'description_unavailable'})):
            repair_job(job)
        self.assertEqual(job['description'], 'Department: Engineering')
        self.assertEqual(job['resume_match_pct'], 20)

    def test_repair_invalidates_old_score_without_changing_identity(self):
        job = {'id':'example:1','description':'','resume_match_pct':20, 'tracking_status':'saved'}
        text = 'Responsibilities: develop Python data pipelines. Required skills include SQL. ' * 5
        with patch('scripts.career.repair_export.retrieve', return_value=(text, {})):
            repair_job(job)
        self.assertEqual(job['id'], 'example:1')
        self.assertEqual(job['tracking_status'], 'saved')
        self.assertIsNone(job['resume_match_pct'])


if __name__ == '__main__':
    unittest.main()
