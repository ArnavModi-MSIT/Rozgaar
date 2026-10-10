import unittest
from fetchers import swissre
class SwissReTests(unittest.TestCase):
 def card(self,location):
  return '<p>Showing 0 of 1</p><div class="JobTeaser"><div class="JobTeaser--title">Analyst</div><div class="JobTeaser--location">Location '+location+'</div><a class="JobTeaser--link" href="/careers/job/Analyst/123"></a></div>'
 def test_india_card(self):
  jobs,total=swissre.parse_listing(self.card('Bangalore, IN')); self.assertEqual(total,1); self.assertEqual(jobs[0]['location'],'Bangalore, India')
 def test_foreign_rejected(self):
  with self.assertRaises(RuntimeError): swissre.parse_listing(self.card('London, GB'))
 def test_failed_page(self):
  with self.assertRaises(RuntimeError): swissre.parse_listing('Forbidden')
 def test_full_description(self):
  text=swissre.parse_detail('<section class="ArticleSection"><div class="richtext"><p>Qualifications</p><p>3 years of experience</p></div></section>')
  self.assertIn('Qualifications\n3 years',text)
if __name__=='__main__': unittest.main()
