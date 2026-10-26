import html,json,unittest
from unittest.mock import patch
from backend.fetchers import publicissapient as ps

def row(i=1):
    sid=f'2026-{i}'
    return dict(id=sid,name='Engineer',countryName='India',city='Gurgaon',jobDetailUrl=f'/job-details/{sid}-engineer')

def page(rows,total=None,start=0):
    return {'response':dict(docs=rows,numFound=len(rows) if total is None else total,start=start)}

def detail(sid='2026-1',body='Responsibilities Python',country='India'):
    props=dict(countryName=country,description='Job ID: '+sid,jobDescriptionSection=dict(title='Job Description',body=body),qualificationDescriptionSection=dict(title='Qualifications',body='TAIL 0-1 years'),companyDetailsSection=dict(body='BOILERPLATE'))
    return '<script type="application/ld+json">SNIPPET</script><div data-cmp-is="careerjobdetailstemplate" data-react-props="'+html.escape(json.dumps(props),quote=True)+'"></div>'

class PublicisTests(unittest.TestCase):
    def test_pagination_uses_received_rows_and_india_query(self):
        with patch.object(ps,'get_json',side_effect=[page([row(1)],2),page([row(2)],2,1)]) as fetch,patch.object(ps,'get_text',side_effect=[detail(),detail('2026-2')]),patch.object(ps.time,'sleep'):
            result=ps.collect()
        self.assertEqual(result.status,'ok');self.assertEqual(len(result),2)
        self.assertEqual([c.kwargs['params']['start'] for c in fetch.call_args_list],[0,1])
        self.assertTrue(all(c.kwargs['params']['country']=='India' for c in fetch.call_args_list))

    def test_full_sections_not_preview_or_boilerplate(self):
        text=ps._description(detail(body='word '*1500),'2026-1')
        self.assertGreater(len(text),6000);self.assertIn('TAIL 0-1 years',text)
        self.assertNotIn('BOILERPLATE',text);self.assertNotIn('SNIPPET',text)

    def test_location_variant_uses_base_requisition_and_keeps_own_identity(self):
        r=row();r['id']='2026-1-99';r['jobDetailUrl']='/job-details/2026-1-99-engineer'
        self.assertEqual(ps._listing(r)['source_id'],'2026-1-99')
        self.assertIn('Python',ps._description(detail(),'2026-1-99'))
        with self.assertRaises(ValueError):ps._description(detail('2026-2'),'2026-1-99')

    def test_foreign_and_untrusted_links_rejected(self):
        for changes in [dict(countryName='USA'),dict(jobDetailUrl='https://evil.example/job-details/2026-1-engineer'),dict(jobDetailUrl='/job-details/2026-2-engineer')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):ps._listing(dict(row(),**changes))
        with self.assertRaises(ValueError):ps._description(detail(country='USA'),'2026-1')

    def test_missing_body_preserves_listing_as_partial(self):
        with patch.object(ps,'get_json',return_value=page([row()])),patch.object(ps,'get_text',return_value=detail(body='')),patch.object(ps.time,'sleep'):
            result=ps.collect()
        self.assertEqual(result.status,'partial');self.assertEqual(result[0]['description'],'')

    def test_bad_schema_fails_and_verified_empty_succeeds(self):
        with patch.object(ps,'get_json',return_value={}),self.assertRaises(RuntimeError):ps.collect()
        with patch.object(ps,'get_json',return_value=page([])):self.assertEqual(ps.collect().status,'ok')

    def test_repeated_page_remains_partial(self):
        with patch.object(ps,'get_json',side_effect=[page([row()],3),page([row()],3,1)]),patch.object(ps,'get_text',return_value=detail()),patch.object(ps.time,'sleep'):
            result=ps.collect()
        self.assertEqual(result.status,'partial');self.assertEqual(len(result),1)

    def test_deadline_and_registration(self):
        with patch.object(ps,'get_json') as fetch,self.assertRaises(RuntimeError):ps.collect(deadline=0)
        fetch.assert_not_called()
        from backend.core.collector import PLATFORMS
        self.assertIn('publicissapient',dict(PLATFORMS))
