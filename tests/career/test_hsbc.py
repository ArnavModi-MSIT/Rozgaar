import unittest
from unittest.mock import patch
from backend.fetchers import hsbc

def row(i=1,**changes):
    r=dict(id=i,name='Engineer',locations=['Delhi, India'],isPrivate=False,canonicalPositionUrl=hsbc.BASE+'/careers/job/'+str(i),job_description='<p>Python responsibilities</p>');r.update(changes);return r

def page(rows,count=None):
    return dict(domain='hsbc.com',positions=rows,count=len(rows) if count is None else count,fuzzyResultsReturned=False)

class HsbcTests(unittest.TestCase):
    def test_pagination_and_full_detail_endpoint(self):
        with patch.object(hsbc,'get_json',side_effect=[page([row()],2),page([row(2)],2),row(),row(2)]) as fetch,patch.object(hsbc.time,'sleep'):
            jobs=hsbc.collect()
        self.assertEqual(jobs.status,'ok');self.assertEqual(len(jobs),2)
        self.assertEqual([c.kwargs['params']['start'] for c in fetch.call_args_list[:2]],[0,1])
        self.assertEqual(fetch.call_args_list[0].kwargs['params']['location'],'India')
        self.assertEqual(fetch.call_args_list[-1].args[1],hsbc.ENDPOINT+'/2')

    def test_full_tail_and_no_other_fields(self):
        r=row(job_description='<p>'+'word '*1500+'</p><p>TAIL qualifications 0-1 years</p>',department='IGNORE',urls=['IGNORE'])
        text=hsbc._description(r,hsbc._listing(r))
        self.assertGreater(len(text),6000);self.assertIn('TAIL qualifications',text);self.assertNotIn('IGNORE',text)

    def test_identity_title_and_private_detail_rejected(self):
        job=hsbc._listing(row())
        for r in [row(2),row(name='Other'),row(isPrivate=True)]:
            with self.subTest(r=r),self.assertRaises(ValueError):hsbc._description(r,job)

    def test_india_evidence_and_url_validation(self):
        for r in [row(locations=['Indiana, USA']),row(locations=[] ,location='London, UK'),row(canonicalPositionUrl='https://evil.example/careers/job/1'),row(canonicalPositionUrl=hsbc.BASE+'/careers/job/2')]:
            with self.subTest(r=r),self.assertRaises(ValueError):hsbc._listing(r)
        r=row(locations=['London, UK','Delhi, India']);self.assertEqual(hsbc._listing(r)['location'],'Delhi, India')

    def test_missing_body_preserves_job(self):
        with patch.object(hsbc,'get_json',side_effect=[page([row()]),row(job_description='')]),patch.object(hsbc.time,'sleep'):
            jobs=hsbc.collect()
        self.assertEqual(jobs.status,'partial');self.assertEqual(jobs[0]['description'],'')

    def test_empty_verified_schema_and_fuzzy_failures(self):
        with patch.object(hsbc,'get_json',return_value=page([])):self.assertEqual(hsbc.collect().status,'ok')
        for p in [{},dict(page([]),fuzzyResultsReturned=True),dict(page([]),count=True)]:
            with patch.object(hsbc,'get_json',return_value=p),self.assertRaises(RuntimeError):hsbc.collect()

    def test_repeated_page_and_later_failure_keep_results(self):
        for p in [page([row()],3),None]:
            with patch.object(hsbc,'get_json',side_effect=[page([row()],3),p,row()]),patch.object(hsbc.time,'sleep'):
                jobs=hsbc.collect()
            self.assertEqual(jobs.status,'partial');self.assertEqual(len(jobs),1)

    def test_deadline_and_registration(self):
        with patch.object(hsbc,'get_json') as fetch,self.assertRaises(RuntimeError):hsbc.collect(deadline=0)
        fetch.assert_not_called()
        from backend.core.collector import PLATFORMS
        self.assertIn('hsbc',dict(PLATFORMS))
