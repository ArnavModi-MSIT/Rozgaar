import unittest
from unittest.mock import patch
from backend.fetchers import siemenssoftware as s

def row(i=1,**kw):
 d=dict(buid=38591,country_exact='India',guid=f'{i:032X}',reqid=str(i),title_exact='Software Engineer',title_slug='software-engineer',location_exact='Pune, IND',html_description='<p>Responsibilities Python</p>');d.update(kw);return d

def page(rows,n=1,total=None,more=False):return dict(jobs=rows,featured_jobs=[],pagination=dict(total=len(rows) if total is None else total,page=n,has_more_pages=more))

class SiemensSoftwareTests(unittest.TestCase):
 def test_scoped_pagination_and_identity_linked_details(self):
  with patch.object(s,'post_json',side_effect=[page([row()],total=2,more=True),page([row(2)],n=2,total=2)]) as search,patch.object(s,'get_json',side_effect=[row(),row(2)]),patch.object(s.time,'sleep'):
   jobs=s.collect()
  self.assertEqual(jobs.status,'ok');self.assertEqual(len(jobs),2)
  self.assertEqual([c.kwargs['json']['data']['page'] for c in search.call_args_list],[1,2])
  self.assertEqual(search.call_args.kwargs['json']['config']['buids'],[38591,38526]);self.assertIn('India',jobs[0]['location']);self.assertIn('/00000000000000000000000000000001/job/',jobs[0]['url'])
 def test_employer_country_and_identity_rejections(self):
  for r in [row(buid=9),row(country_exact='USA'),row(title_exact=''),row(guid='not-guid')]:
   with self.assertRaises(ValueError):s._listing(r)
  for r in [row(2),row(deleted_at='today')]:
   with self.assertRaises(ValueError):s._description(r,s._listing(row()))
 def test_full_description_tail_is_retained(self):
  text=s._description(row(html_description='<p>'+'word '*1500+'</p><p>Qualifications: minimum 5 years</p>'),s._listing(row()))
  self.assertGreater(len(text),6000);self.assertIn('minimum 5 years',text)
 def test_missing_detail_stays_partial_not_search_snippet(self):
  with patch.object(s,'post_json',return_value=page([row()])),patch.object(s,'get_json',return_value=None),patch.object(s.time,'sleep'):
   jobs=s.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(jobs[0]['description'],'')
 def test_empty_schema_and_repeated_pages(self):
  with patch.object(s,'post_json',return_value=page([])):self.assertEqual(s.collect().status,'ok')
  with patch.object(s,'post_json',return_value={}),self.assertRaises(RuntimeError):s.collect()
  with patch.object(s,'post_json',side_effect=[page([row()],total=3,more=True),page([row()],n=2,total=3,more=True)]),patch.object(s,'get_json',return_value=row()),patch.object(s.time,'sleep'):
   jobs=s.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(len(jobs),1)
 def test_deadline_and_registration(self):
  with patch.object(s,'post_json') as fetch,self.assertRaises(RuntimeError):s.collect(deadline=0)
  fetch.assert_not_called()
  from backend.core.collector import PLATFORMS
  self.assertIn('siemenssoftware',dict(PLATFORMS))

 def test_location_variants_and_underscore_slugs_preserved(self):
  a=row(title_slug='engineer_india');b=row(2,reqid='1',location_exact='Pune, IND')
  with patch.object(s,'post_json',return_value=page([a,b])),patch.object(s,'get_json',side_effect=[a,b]),patch.object(s.time,'sleep'):
   jobs=s.collect()
  self.assertEqual(jobs.status,'ok');self.assertEqual(len({j['source_id'] for j in jobs}),2)
  self.assertIn('engineer_india',jobs[0]['url'])
  with self.assertRaises(ValueError):s._description(row(reqid='99'),s._listing(row()))
