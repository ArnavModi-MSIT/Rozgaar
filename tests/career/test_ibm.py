import unittest
from unittest.mock import patch

from backend.fetchers import ibm


def hit(sid, **changes):
    source = dict(title='Software Engineer', url=f'https://careers.ibm.com/careers/JobDetail?jobId={sid}',
                  body='<p>Full posting</p><p>Qualifications: Python and SQL</p>',
                  field_keyword_05='India', field_keyword_19='Bangalore, IN')
    source.update(changes)
    return {'_source':source}


def page(rows, total, **extra):
    return dict(hits={'total':{'value':total,'relation':'eq'},'hits':rows}, **extra)


class IBMTests(unittest.TestCase):
    def test_paginates_by_received_rows_and_preserves_qualification_tail(self):
        body='<p>'+'Introduction '*700+'</p><p>Qualifications: 0-1 years</p>'
        with patch.object(ibm,'post_json',side_effect=[page([hit(1,body=body),hit(2)],3),page([hit(3)],3)]) as post, patch.object(ibm.time,'sleep'):
            result=ibm.collect()
        self.assertEqual(result.status,'ok')
        self.assertEqual([j['source_id'] for j in result],['1','2','3'])
        self.assertIn('Qualifications: 0-1 years',result[0]['description'])
        self.assertGreater(len(result[0]['description']),6000)
        self.assertEqual([call.kwargs['json']['from'] for call in post.call_args_list],[0,2])
        self.assertIn('body',post.call_args.kwargs['json']['_source'])
        self.assertEqual(post.call_args.kwargs['json']['sort'],[{'_id':'asc'}])
        self.assertEqual(post.call_args.kwargs['json']['query']['bool']['must'],[{'term':{'field_keyword_05':'India'}}])

    def test_explicit_country_and_stable_job_identity(self):
        for changes in [dict(field_keyword_05='Indiana'),dict(field_keyword_05='United States'),
                        dict(url='https://other.example/careers/JobDetail?jobId=1'),
                        dict(url='https://careers.ibm.com/careers/JobDetail?jobId=1&jobId=2'),dict(title='')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                ibm._record(hit(1,**changes))
        job=ibm._record(hit(1,field_keyword_05=['United States','India'],field_keyword_19=['Bangalore, IN','Hyderabad, IN']))
        self.assertEqual(job['location'],'Bangalore, IN; Hyderabad, IN, India')

    def test_missing_body_is_partial_not_a_snippet_substitution(self):
        with patch.object(ibm,'post_json',return_value=page([hit(1,body='',description='Tiny snippet')],1)):
            result=ibm.collect()
        self.assertEqual(result.status,'partial')
        self.assertEqual(result[0]['description'],'')
        self.assertIn('full description unavailable',result.error)

    def test_bad_first_page_fails_but_late_failure_preserves_jobs(self):
        for response in [None,{},dict(hits={'hits':[]}),dict(hits={'total':True,'hits':[]})]:
            with self.subTest(response=response),patch.object(ibm,'post_json',return_value=response),self.assertRaises(RuntimeError):
                ibm.collect()
        with patch.object(ibm,'post_json',side_effect=[page([hit(1)],2),None]),patch.object(ibm.time,'sleep'):
            result=ibm.collect()
        self.assertEqual(result.status,'partial')
        self.assertEqual(len(result),1)

    def test_repeated_page_and_total_drift_are_partial(self):
        with patch.object(ibm,'post_json',side_effect=[page([hit(1)],3),page([hit(1)],4)]),patch.object(ibm.time,'sleep'):
            result=ibm.collect()
        self.assertEqual(len(result),1)
        self.assertEqual(result.status,'partial')
        self.assertIn('repeated page',result.error)
        self.assertIn('total changed',result.error)

    def test_verified_empty_and_deadline_are_distinct(self):
        with patch.object(ibm,'post_json',return_value=page([],0)):
            self.assertEqual(ibm.collect().status,'ok')
        with patch.object(ibm,'post_json') as post,self.assertRaises(RuntimeError):
            ibm.collect(deadline=0)
        post.assert_not_called()

    def test_search_timeout_and_lower_bound_are_not_complete(self):
        data=page([hit(1)],1,timed_out=True)
        data['hits']['total']['relation']='gte'
        with patch.object(ibm,'post_json',side_effect=[data,page([],1)]),patch.object(ibm.time,'sleep'):
            result=ibm.collect()
        self.assertEqual(result.status,'partial')
        self.assertIn('lower bound',result.error)
        self.assertIn('timed out',result.error)

    def test_registered_and_displayed_as_ibm(self):
        import backend.config as config
        from backend.core.collector import PLATFORMS
        self.assertIn('ibm',dict(PLATFORMS))
        self.assertEqual(config.DISPLAY_NAMES['ibm'],'IBM')
