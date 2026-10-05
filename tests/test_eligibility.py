import unittest
from core.eligibility import eligibility_evidence
class EligibilityTests(unittest.TestCase):
    def test_unknown_is_not_approval(self):
        result=eligibility_evidence("")
        self.assertIsNone(result["minimum_years"])
        self.assertTrue(result["needs_review"])
    def test_requirements_with_exact_evidence(self):
        text="Bachelor degree required.\nGraduating in 2027.\nMust have Python and SQL."
        result=eligibility_evidence(text,["python"])
        self.assertEqual(result["education_evidence"],["Bachelor degree required."])
        self.assertEqual(result["graduation_evidence"],["Graduating in 2027."])
        self.assertIn("sql",result["missing_mandatory_skills"])
    def test_preferred_skills_are_not_mandatory(self):
        result=eligibility_evidence("Preferred Qualifications:\nPython required.")
        self.assertEqual(result["mandatory_skills"],[])
