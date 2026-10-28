import unittest
from unittest.mock import patch
from backend.fetchers import barracuda as b

HTML='<div data-cmp-is="CareersRoom"><div data-cmp-hook-careers-room="cardsContainerFeatured" data-panel-endpoint="/content/barracuda-corp/us/en/company/careers/test.careers.json"></div></div>'
def row(**kw):
 r=dict(eId='abc123',title='Software Engineer',location='Bangalore, India',postingType='External',detailLink='https://app.jobvite.com/CompanyJobs/Job.aspx?j=abc123',description='<p>Python responsibilities</p>',customField=[dict(key='internal',value='OMIT')],applyLink='OMIT');r.update(kw);return r

def feed(rows):return dict(jobs=rows,locations=['Bangalore, India'],categories=['Engineering'])

class BarracudaTests(unittest.TestCase):
 def test_scope_and_fields(self):
  with patch.object(b,'get_text',return_value=HTML),patch.object(b,'get_json',return_value=feed([row(),row(eId='foreign',location='Remote - Indonesia')])):
   jobs=b.collect()
  self.assertEqual(jobs.status,'ok');self.assertEqual(len(jobs),1)
  self.assertEqual(set(jobs[0]),{'company','source_id','title','location','url','description'})
  self.assertNotIn('OMIT',str(jobs[0]))
 def test_full_description_tail(self):
  text=b._job(row(description='<p>'+'word '*1400+'</p><p>Qualifications: 5 years</p>'))['description']
  self.assertGreater(len(text),6000);self.assertIn('Qualifications: 5 years',text)
 def test_identity_link_and_internal_posting_rejected(self):
  for r in [row(title=''),row(postingType='Internal'),row(detailLink='https://evil.example/CompanyJobs/Job.aspx?j=abc123'),row(detailLink='https://app.jobvite.com/CompanyJobs/Job.aspx?j=other')]:
   with self.assertRaises(ValueError):b._job(r)
 def test_missing_body_and_malformed_rows_are_partial(self):
  with patch.object(b,'get_text',return_value=HTML),patch.object(b,'get_json',return_value=feed([row(description=''),row(eId='x',title='')])):
   jobs=b.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(jobs[0]['description'],'')
 def test_layout_schema_and_empty_feed(self):
  with self.assertRaises(ValueError):b._endpoint('<html>Access denied</html>')
  with patch.object(b,'get_text',return_value=HTML),patch.object(b,'get_json',return_value={}):
   with self.assertRaises(RuntimeError):b.collect()
  with patch.object(b,'get_text',return_value=HTML),patch.object(b,'get_json',return_value=feed([])):self.assertEqual(b.collect().status,'ok')
 def test_deadline_registration_and_duplicate(self):
  with patch.object(b,'get_text') as fetch,self.assertRaises(RuntimeError):b.collect(deadline=0)
  fetch.assert_not_called()
  with patch.object(b,'get_text',return_value=HTML),patch.object(b,'get_json',return_value=feed([row(),row()])):
   jobs=b.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(len(jobs),1)
  from backend.core.collector import PLATFORMS
  self.assertIn('barracuda',dict(PLATFORMS))
