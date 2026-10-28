import unittest
from unittest.mock import patch
from backend.fetchers import teradata as t

def row(id='1',**kw):
 r=dict(key=id,title='Data Engineer',descriptionHTML='<p>Python responsibilities</p>',primaryPlace={'name':'Hyderabad, Telangana, India'},places={'nodes':[]});r.update(kw);return r

def page(rows,total=None,more=False,cursor='next'):
 return {'data':{'searchJobPostings':{'results':dict(nodes=rows,totalCount=len(rows) if total is None else total,pageInfo=dict(hasNextPage=more,endCursor=cursor))}}}
class TeradataTests(unittest.TestCase):
 def test_cursor_and_india_filter(self):
  with patch.object(t,'post_json',side_effect=[page([row()],2,True),page([row('2')],2)]) as fetch,patch.object(t.time,'sleep'):
   jobs=t.collect()
  self.assertEqual(jobs.status,'ok');self.assertEqual(len(jobs),2)
  self.assertEqual(fetch.call_args_list[1].kwargs['json']['variables']['after'],'next')
  self.assertEqual(fetch.call_args.kwargs['json']['variables']['filters'],{'location':[{'address':'India'}]})
 def test_positive_india_evidence_and_title_identity(self):
  for r in [row(key=''),row(title=''),row(primaryPlace={'name':'Indiana, USA'})]:
   with self.assertRaises(ValueError):t._job(r)
  j=t._job(row(primaryPlace={'name':'San Diego, USA'},places={'nodes':[{'name':'Pune, India'}]}))
  self.assertEqual(j['location'],'Pune, India');self.assertEqual(j['url'],t.BASE+'/jobs/1/data-engineer')
 def test_full_body_tail(self):
  j=t._job(row(descriptionHTML='<p>'+'word '*1500+'</p><p>TAIL: 6 years experience</p>'))
  self.assertGreater(len(j['description']),6000);self.assertIn('TAIL:',j['description'])
 def test_missing_description_and_later_errors_keep_jobs(self):
  with patch.object(t,'post_json',side_effect=[page([row(descriptionHTML='')],2,True),{'errors':[{'message':'error'}]}]),patch.object(t.time,'sleep'):
   jobs=t.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['description'],'')
 def test_verified_empty_schema_and_repeated_cursor(self):
  with patch.object(t,'post_json',return_value=page([])):self.assertEqual(t.collect().status,'ok')
  with patch.object(t,'post_json',return_value={}),self.assertRaises(RuntimeError):t.collect()
  with patch.object(t,'post_json',side_effect=[page([row()],3,True),page([row('2')],3,True)]),patch.object(t.time,'sleep'):
   jobs=t.collect()
  self.assertEqual(jobs.status,'partial');self.assertIn('cursor',jobs.error)
 def test_deadline_and_registration(self):
  with patch.object(t,'post_json') as fetch,self.assertRaises(RuntimeError):t.collect(deadline=0)
  fetch.assert_not_called()
  from backend.core.collector import PLATFORMS
  self.assertIn('teradata',dict(PLATFORMS))
