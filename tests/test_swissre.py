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
 def test_mobile_desktop_multi_location_card(self):
  html=self.card('unused').replace('Location unused','<span class="is-visible-mobile-portrait">Bangalore, IN <span aria-hidden="true">+ 1</span></span><span class="is-hidden-mobile-portrait">Bangalore, IN <span aria-hidden="true">+ 1 more</span></span><span class="visuallyhidden">and Hyderabad</span>')
  html=html.replace('</a>','<span class="visuallyhidden">Analyst,\n\t Bangalore (KA, IN) and Hyderabad (TG, IN).</span></a>')
  jobs,total=swissre.parse_listing(html)
  self.assertEqual(total,1);self.assertEqual(jobs[0]['location'],'Bangalore, India; Hyderabad, India')
 def test_country_evidence_overrides_mixed_location_visual_text(self):
  html=self.card('Location summaries').replace('</a>','Analyst, London (LDN, GB) and Bangalore (KA, IN).</a>')
  jobs,_=swissre.parse_listing(html);self.assertEqual(jobs[0]['location'],'Bangalore, India')
 def test_visual_primary_without_accessible_pairs(self):
  html=self.card('unused').replace('Location unused','<span class="is-hidden-mobile-portrait">Bangalore, IN <span aria-hidden="true">+ 1 more</span></span>')
  jobs,_=swissre.parse_listing(html);self.assertEqual(jobs[0]['location'],'Bangalore, India')
 def test_foreign_accessible_country_not_relabelled_from_city_name(self):
  html=self.card('Bangalore, IN').replace('</a>','Analyst, London (LDN, GB).</a>')
  with self.assertRaises(RuntimeError):swissre.parse_listing(html)
 def test_full_description(self):
  text=swissre.parse_detail('<section class="ArticleSection"><div class="richtext"><p>Qualifications</p><p>3 years of experience</p></div></section>')
  self.assertIn('Qualifications\n3 years',text)
if __name__=='__main__': unittest.main()
