import unittest
from backend.core.experience import extract_min_experience, extract_preferred_experience
class RoleYearsTests(unittest.TestCase):
 def test_portcast_requirement(self):
  text='At least 2-3+ years in a Data Analyst or Business Analyst role, preferably in a product-based, lean startup particularly in logistics, ecommerce or B2B SaaS data-heavy domain.'
  self.assertEqual(extract_min_experience(text),2)
 def test_range_upper_plus(self):
  for text in ['2-3+ years of experience','2–3+ years of experience','2 to 3+ years of experience']:
   self.assertEqual(extract_min_experience(text),2)
 def test_role_preference_is_separate(self):
  text='Preferably 2-3+ years in a data analyst role.'
  self.assertIsNone(extract_min_experience(text)); self.assertEqual(extract_preferred_experience(text),2)
 def test_unrelated_years_excluded(self):
  for text in ['At least 3 years in business.', '2 years in a degree program.', '5 years as an established company.']:
   self.assertIsNone(extract_min_experience(text),text)
if __name__=='__main__': unittest.main()
