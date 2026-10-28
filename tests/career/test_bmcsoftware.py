import unittest
from unittest.mock import patch
from backend.fetchers import bmcsoftware as b
URL=b.BASE+'/Careers/JobDetail/Engineer/1'
def page(total=1,next=False):
 return '<div class="list-controls__text__legend">1-6 of '+str(total)+' results</div><article class="article--result"><h3><a href="'+URL+'">Engineer</a></h3><span class="list-item-location">Pune, India</span></article>'+('<a aria-label="Go to Next Page, Number 2" href="'+b.SEARCH_URL+'&jobOffset=6">Next</a>' if next else '')
def detail(id='1',country='India',body='Python responsibilities'):
 return '<div class="detailData">'+''.join('<div class="article__content__view__field"><div class="article__content__view__field__label">'+k+'</div><div class="article__content__view__field__value">'+v+'</div></div>' for k,v in [('Job ID',id),('Country',country)])+'</div><div class="detailDescription"><div class="article__content">'+body+'</div></div><form>OMIT FORM</form>'
class BmcTests(unittest.TestCase):
 def test_pagination_preserves_india_and_distinct_ids(self):
  with patch.object(b,'get_text',side_effect=[page(2,True),page(2).replace('/Engineer/1','/Engineer/2'),detail(),detail('2')]) as fetch,patch.object(b.time,'sleep'):
   jobs=b.collect()
  self.assertEqual(jobs.status,'ok');self.assertEqual(len(jobs),2);self.assertIn('jobOffset=6',fetch.call_args_list[1].args[1])
 def test_scope_and_untrusted_urls_rejected(self):
  for url in ['https://evil.example/Careers/SearchJobs/',b.SEARCH_URL.replace('%5B9406%5D','%5B1234%5D')]:
   with self.assertRaises(ValueError):b._url(url)
 def test_identity_country_and_full_body(self):
  job=b._page(page())[0][0]
  text=b._description(detail(body='word '*1500+'TAIL QUALIFICATIONS'),job)
  self.assertGreater(len(text),6000);self.assertIn('TAIL QUALIFICATIONS',text);self.assertNotIn('OMIT FORM',text)
  for html in [detail('2'),detail(country='USA')]:
   with self.assertRaises(ValueError):b._description(html,job)
 def test_failed_detail_preserves_listing(self):
  with patch.object(b,'get_text',side_effect=[page(),None]),patch.object(b.time,'sleep'):jobs=b.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(jobs[0]['description'],'')
 def test_repeated_page_partial_and_bad_schema_failure(self):
  with patch.object(b,'get_text',side_effect=[page(3,True),page(3,True),detail()]),patch.object(b.time,'sleep'):jobs=b.collect()
  self.assertEqual(jobs.status,'partial');self.assertEqual(len(jobs),1)
  with patch.object(b,'get_text',return_value='<html>Denied</html>'),self.assertRaises(RuntimeError):b.collect()
 def test_deadline_and_registration(self):
  with patch.object(b,'get_text') as fetch,self.assertRaises(RuntimeError):b.collect(deadline=0)
  fetch.assert_not_called()
  from backend.core.collector import PLATFORMS
  self.assertIn('bmcsoftware',dict(PLATFORMS))
