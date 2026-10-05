import unittest
from core.experience import extract_min_experience
from fetchers.amazon import _parse_job

BASIC="4+ years of compliance program management, legal, governance, audit, risk/loss prevention, or equivalent experience"
PREFERRED="3+ years of program requirements definition and data and metrics leveraging to drive improvements experience"
class QualificationExperienceTests(unittest.TestCase):
    def test_amazon_long_basic_clause(self):
        self.assertEqual(extract_min_experience("Basic Qualifications:\n"+BASIC+"\nPreferred Qualifications:\n"+PREFERRED),4)
    def test_flattened_headings(self):
        self.assertEqual(extract_min_experience("Basic Qualifications "+BASIC+" Preferred Qualifications "+PREFERRED),4)
    def test_preferred_only_is_unknown(self):
        self.assertIsNone(extract_min_experience("Preferred Qualifications:\n"+PREFERRED))
    def test_range_uses_lower_bound(self):
        self.assertEqual(extract_min_experience("Basic Qualifications: 2-5 years of extensive relevant engineering and systems development experience"),2)
    def test_unrelated_years_are_not_requirements(self):
        self.assertIsNone(extract_min_experience("Benefits: We have 10 years in business. Certification is valid for 2 years."))
    def test_amazon_retains_qualifications_after_long_description(self):
        job=_parse_job({"description":"Company background "*600,"basic_qualifications":BASIC,"preferred_qualifications":PREFERRED})
        self.assertIn(BASIC,job["description"])
        self.assertEqual(extract_min_experience(job["description"]),4)
