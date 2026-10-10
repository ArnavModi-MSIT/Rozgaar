import unittest
from unittest.mock import patch
from fetchers import ea
class EATests(unittest.TestCase):
 def test_listing_scope(self):
  html='<p>1 results</p><div class="article__header__text"><h3 class="article__header__text__title"><a href="https://jobs.ea.com/en_US/careers/JobDetail/Intern/123">Intern</a></h3><span class="list-item-location">Hyderabad, India</span></div>'
  rows,total=ea._page(html); self.assertEqual(total,1); self.assertEqual(rows[0]['source_id'],'123'); self.assertEqual(rows[0]['location'],'Hyderabad, India')
 def test_missing_total_fails(self):
  with self.assertRaises(RuntimeError): ea._page('Access denied')
 def test_long_description_retained(self):
  html='<div class="article__content__view__field">'+('x '*13000)+'Qualifications: 4 years experience</div>'
  with patch.object(ea,'_get',return_value=html): text=ea._description({'url':'https://jobs.ea.com/detail'},None)
  self.assertIn('4 years experience',text)
if __name__=='__main__': unittest.main()
