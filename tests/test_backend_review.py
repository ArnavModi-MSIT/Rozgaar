"""Regressions found while reviewing filtering and matcher section behavior."""
import unittest

from core.experience import extract_min_experience, extract_preferred_experience, experience_requirements
from core.match_sections import eligibility_checks, job_parts


class BackendReviewTests(unittest.TestCase):
    def test_explicit_title_years_without_description(self):
        self.assertEqual(experience_requirements("", "Data Analytics Manager | 8 -12 Years"), (8,None))
        self.assertEqual(experience_requirements("", "Data Engineer | 2.5+ years"), (2.5,None))
        self.assertEqual(experience_requirements("", "Data Engineer | 3-5 years preferred"), (None,3))
        self.assertEqual(experience_requirements("", "Senior Data Engineer"), (None,None))
        self.assertEqual(experience_requirements("", "Intern - 1 year programme"), (None,None))
        self.assertEqual(experience_requirements("", "Engineer - 2-3 years contract"), (None,None))
    def test_overall_years_not_erased_by_smaller_skill_requirement(self):
        overall = "5+ years of professional software development experience."
        sql = "1+ years of experience with SQL."
        for clauses in [(overall, sql), (sql, overall)]:
            self.assertEqual(extract_min_experience(
                "Basic Qualifications:\n" + "\n".join(clauses)), 5)
        self.assertEqual(extract_min_experience(overall + "\n" + sql), 5)

    def test_ranges_and_explicit_alternatives_keep_lower_bar(self):
        self.assertEqual(extract_min_experience(
            "Required Qualifications:\n2-5 years of software engineering experience."), 2)
        self.assertEqual(extract_min_experience(
            "Required Qualifications:\n5 years of engineering experience with a bachelor's degree "
            "or 3 years of engineering experience with a master's degree."), 3)
        self.assertEqual(extract_min_experience(
            "Required Qualifications:\n5 years of professional experience.\n"
            "3 years of SQL experience or 1 year of SQL experience with certification."), 5)

    def test_decimal_years_not_parsed_as_fractional_suffix(self):
        self.assertEqual(extract_min_experience(
            "Required Qualifications:\n2.5 years of experience in data engineering."), 2.5)
        self.assertEqual(extract_min_experience("1.5-3 years of SQL experience."), 1.5)
        self.assertEqual(extract_preferred_experience(
            "Preferred Qualifications:\n2.5 years of experience in data engineering."), 2.5)

    def test_preferred_requirements_do_not_override_required_years(self):
        text = ("Basic Qualifications:\n1 year of SQL experience.\n"
                "Preferred Qualifications:\n5 years of professional software experience.\n"
                "1 year of experience with Spark.")
        self.assertEqual(extract_min_experience(text), 1)
        self.assertEqual(extract_preferred_experience(text), 5)

    def test_preferred_only_description_remains_in_embedding_sections(self):
        for text in ["Preferred Qualifications:\nPython and SQL",
                     "<h2>Preferred Qualifications</h2><p>Python and SQL</p>"]:
            pair = job_parts("Data Engineer", text)
            self.assertTrue(all("Python and SQL" in section for section in pair))

    def test_graduation_range_and_alternative_are_unknown(self):
        for requirement in ["Graduating in 2027-2028", "Graduating in 2027 or 2028"]:
            checks = eligibility_checks("Required Qualifications:\n" + requirement,
                                        "India", "Expected graduation: 2028", set())
            self.assertEqual(checks[2]["status"], "unknown")
        checks = eligibility_checks("Required Qualifications:\nGraduating in 2028",
                                    "India", "Graduation: 2027-2028", set())
        self.assertEqual(checks[2]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
