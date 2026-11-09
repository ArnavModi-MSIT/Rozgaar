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
 def test_unitless_years_of_experience_label(self):
  # IBM Careers: "Years of Experience:5 - 10" has no unit after the number.
  ibm='Technical Solution Optimization: Experience applying technical expertise.\n\nYears of Experience:5 - 10\n\nABOUT BUSINESS UNIT'
  self.assertEqual(extract_min_experience(ibm),5)
  self.assertEqual(extract_min_experience('<p>Years of Experience: 3+</p>'),3)
  self.assertEqual(extract_min_experience('Experience (years): 0-1'),0)
  self.assertIsNone(extract_min_experience('Years of Experience: 6 months'))
 def test_ibm_years_range_with_non_breaking_spaces(self):
  # Live IBM markup (jobId 131764): the range is "8&nbsp;-&nbsp;14" and follows a "Preferred" heading.
  ibm=('<div><strong>Preferred technical and professional experience</strong></div>'
       '<p>&bull; Open Source Technologies: Exposure to Airflow, dbt, Spark.</p>'
       '<div class="article__content__view__field__value"><strong>Years of Experience:</strong><br>8&nbsp;-&nbsp;14</div>'
       '<h3>ABOUT BUSINESS UNIT</h3><p>IBM Consulting is IBM\u2019s consulting business.</p>')
  self.assertEqual(extract_min_experience(ibm),8)
  self.assertEqual(extract_min_experience('Years of Experience: 8\xa0-\xa014'),8)
  self.assertEqual(extract_min_experience('Years of Experience: 3\xa0+'),3)
  self.assertIsNone(extract_min_experience('Years of Experience: 6\xa0months'))
if __name__=='__main__': unittest.main()
