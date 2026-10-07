import unittest
from core.experience import extract_min_experience, extract_preferred_experience
from fetchers.amazon import _parse_job

BASIC="4+ years of compliance program management, legal, governance, audit, risk/loss prevention, or equivalent experience"
PREFERRED="3+ years of program requirements definition and data and metrics leveraging to drive improvements experience"
class QualificationExperienceTests(unittest.TestCase):
    def test_deloitte_preceding_certification_preference_does_not_hide_years(self):
        text = "Key Responsibilities\nSupport analytics.\nKey skills required:\nCertifications CFE, CAMS or FICO are a plus.\n4-7 years of experience in FRM space within a Risk OEM.\nExposure to Python is preferred."
        self.assertEqual(extract_min_experience(text),4)
        self.assertIsNone(extract_preferred_experience(text))

    def test_paytm_preferred_years_are_separate(self):
        text = "Preferred Qualifications\nBachelors degree. MBA is preferred.\n5–10 years of experience in Growth, Marketing, or Business roles within lending.\nRequired Skills\nSQL"
        self.assertIsNone(extract_min_experience(text))
        self.assertEqual(extract_preferred_experience(text), 5)
        self.assertGreater(max(extract_min_experience(text) or -1, extract_preferred_experience(text) or -1), 1)

    def test_required_preferred_and_inline_preference(self):
        text = "Basic Qualifications:\n1 year of SQL experience\nPreferred Qualifications:\n3 years of Python experience\nResponsibilities:\nMaintain pipelines"
        self.assertEqual(extract_min_experience(text), 1)
        self.assertEqual(extract_preferred_experience(text), 3)
        self.assertEqual(extract_preferred_experience("5+ years of data engineering experience preferred."), 5)
        self.assertIsNone(extract_preferred_experience("Preferred Qualifications: Certification valid for 5 years. We have 10 years in business."))

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

    def test_bosch_experience_section_with_separate_preference(self):
        text="Educational qualifications: certification will be preferred.\nExperience:\n5+ years of rich experience with Data provisioning within Supply Chain. (prior experience collaborating with global teams is highly preferred).\nBusiness & Professional Skills"
        self.assertEqual(extract_min_experience(text),5)
    def test_experience_section_explicit_preference_is_unknown(self):
        self.assertIsNone(extract_min_experience("Experience: 5+ years of data engineering experience preferred."))
