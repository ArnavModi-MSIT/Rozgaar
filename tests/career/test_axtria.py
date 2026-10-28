import unittest
from unittest.mock import patch
from backend.fetchers import axtria as a

def card(title='Engineer',location='Noida, India',href='https://career10.successfactors.com/sfcareer/jobreqcareer?jobId=123&company=axtriaindiP',attr=''):
 return f'<div class="career-bottom-tabs-manual-block"><div class="career-bottom-tabs-manual-left"><p>{title}</p><p>{location}</p></div><a class="career-job-link" {attr} href="{href}">View Job</a></div>'
def listing(cards):return '<div id="fde-career"><div class="career-bottom-tabs-manual">'+cards+'</div></div>'
def detail(id='123',body='Python responsibilities'):
 return f'<title>Career Opportunities: Engineer ({id})</title><div class="joqReqDescription"><div class="externalPosting">{body}</div></div><form>PRIVATE FORM</form>'
class AxtriaTests(unittest.TestCase):
 def test_india_fde_scope_and_no_foreign(self):
  jobs,errors=a._list(listing(card(location='Hyderabad',attr='data-india-job="true"')+card(location='All India')+card(location='Boston, MA')))
  self.assertEqual(len(jobs),1);self.assertEqual(errors,[]);self.assertEqual(jobs[0]['location'],'Hyderabad, India')
 def test_linkedin_retained_without_fetching_description(self):
  html=listing(card(href='https://www.linkedin.com/jobs/view/12345/?trk=foo'))
  with patch.object(a,'get_text',return_value=html) as fetch:jobs=a.collect()
  self.assertEqual(fetch.call_count,1);self.assertEqual(jobs.status,'partial');self.assertEqual(jobs[0]['description'],'')
 def test_full_body_identity_and_forms(self):
  text=a._description(detail(body='word '*1500+'TAIL QUALIFICATIONS'),'123')
  self.assertGreater(len(text),6000);self.assertIn('TAIL QUALIFICATIONS',text);self.assertNotIn('PRIVATE FORM',text)
  with self.assertRaises(ValueError):a._description(detail(id='999'),'123')
 def test_failed_detail_keeps_listing(self):
  with patch.object(a,'get_text',side_effect=[listing(card()),'<p>No longer available</p>']):jobs=a.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['description'],'')
 def test_published_view_link_preserved_untrusted_link_rejected(self):
  url='https://career10.successfactors.com/sfcareer/jobreqcareerpvt?jobId=123&company=axtriaindiP&st='+'A'*40
  jobs,_=a._list(listing(card(href=url)));self.assertEqual(jobs[0]['url'],url)
  jobs,errors=a._list(listing(card(href='https://evil.example/jobs/1')));self.assertEqual(jobs,[]);self.assertTrue(errors)
 def test_schema_empty_deadline_and_registration(self):
  with self.assertRaises(ValueError):a._list('<html>Denied</html>')
  with patch.object(a,'get_text',return_value=listing('')):self.assertEqual(a.collect().status,'ok')
  with patch.object(a,'get_text') as fetch,self.assertRaises(RuntimeError):a.collect(deadline=0)
  fetch.assert_not_called()
  from backend.core.collector import PLATFORMS
  self.assertIn('axtria',dict(PLATFORMS))
