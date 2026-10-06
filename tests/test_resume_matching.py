import unittest
from unittest.mock import patch
import pandas as pd
import torch
from core.match_sections import sections, weighted_skills, eligibility_checks, resume_parts
from core.matcher import embed_jobs_incremental, rank_by_resume


class Tokenizer:
    def encode(self, text, **kwargs):
        return text.split()
    def decode(self, tokens, **kwargs):
        return " ".join(tokens)


class Model:
    tokenizer = Tokenizer()
    def __init__(self):
        self.seen = []
    def encode(self, texts, **kwargs):
        self.seen.extend(texts)
        return torch.tensor([[1.0 if "sql" in text.lower() else 0.0,
                              1.0 if "pipeline" in text.lower() else 0.0,
                              .2] for text in texts])


class ResumeMatchingTests(unittest.TestCase):
    def test_required_and_preferred_have_different_weights(self):
        desc = "Required Qualifications:\nSQL\nPreferred Qualifications:\nPython"
        sql = weighted_skills(desc, {"sql", "python"}, {"sql"})
        python = weighted_skills(desc, {"sql", "python"}, {"python"})
        self.assertEqual(sql[0], 75)
        self.assertEqual(python[0], 25)
        self.assertEqual(sql[1], {"sql"})

    def test_inline_and_html_headings_and_custom_skill(self):
        desc = "<h2>Requirements</h2><p>dbt</p><h2>Preferred Skills</h2><p>SQL</p>"
        self.assertEqual(weighted_skills(desc, {"dbt", "sql"}, {"dbt"})[1], {"dbt"})
        self.assertEqual(sections("Skills: SQL\nProjects:\nBuilt pipeline")["skills"], "SQL")
        self.assertTrue(resume_parts("Projects:\nBuilt pipeline")[1])
        self.assertFalse(resume_parts("SQL developer")[1])

    def test_no_invented_experience_or_eligibility(self):
        checks = eligibility_checks("4+ years of experience required. Bachelor degree required. Graduating in 2028.", "India", "Projects 2020-2026. Education 2027.", {"sql"})
        self.assertEqual(checks[0]["status"], "unknown")
        self.assertEqual(checks[2]["status"], "unknown")
        self.assertEqual(checks[-1]["status"], "mismatch")
        checks = eligibility_checks("4+ years of experience required", "Malaysia", "1 year of professional experience", set())
        self.assertEqual(checks[0]["status"], "mismatch")
        self.assertEqual(checks[1]["status"], "mismatch")

    def test_explicit_graduation_year_and_ambiguous_dates(self):
        checks = eligibility_checks("Required Qualifications:\nGraduating in 2028", "India", "Education:\nExpected graduation: 2027", set())
        self.assertEqual(checks[2]["status"], "mismatch")
        checks = eligibility_checks("Required Qualifications:\nGraduating in 2028", "India", "Education:\n2024-2027", set())
        self.assertEqual(checks[2]["status"], "unknown")

    def test_api_explanations_and_clear_without_database_writes(self):
        from api import data
        df = pd.DataFrame([dict(id="a", title="Data Engineer", company="test", location="India", url="https://example.com", source="test", category="", skills="sql", experience_years=0, first_seen=pd.Timestamp("2026-10-06"), last_seen=pd.Timestamp("2026-10-06"), is_remote=False,is_ncr=False,is_india=True,description="SQL required")])
        state = dict(key="test",text="SQL",skills={"sql"},scores={"a":75.0},explanations={"a":{"missing_required":[]}})
        with patch.object(data, "_resume", state), patch.object(data,"get_jobs_df",return_value=df):
            self.assertEqual(data.job_list_payload(df)[0]["match_explanation"],state["explanations"]["a"])
            self.assertEqual(data.job_detail_payload("a")["match_explanation"],state["explanations"]["a"])
            data.clear_resume()
            self.assertIsNone(data.job_list_payload(df)[0]["match_explanation"])

    @patch("core.matcher.get_model")
    def test_late_requirements_cache_migration_and_reuse(self, get_model):
        model = Model(); get_model.return_value = model
        df = pd.DataFrame([dict(id="a", title="Data Engineer", description="Responsibilities:\n" + "boilerplate "*700 + "\nRequired Qualifications:\nSQL pipeline", skills="sql")])
        embeddings, cache, count = embed_jobs_incremental(df, {"a": ("old", torch.ones(3))})
        self.assertEqual(tuple(embeddings.shape), (1,2,3))
        self.assertTrue(any("SQL pipeline" in text for text in model.seen))
        self.assertTrue(all(len(text.split()) <= 192 for text in model.seen))
        self.assertEqual(count,1)
        self.assertEqual(embed_jobs_incremental(df,cache)[2],0)
        changed = df.copy(); changed.loc[0,"description"] += "\nKafka"
        self.assertEqual(embed_jobs_incremental(changed,cache)[2],1)

    @patch("core.matcher.get_model")
    def test_required_skill_gap_changes_rank_and_explanation(self, get_model):
        get_model.return_value = Model()
        df = pd.DataFrame([
            dict(id="intern",title="Data Engineer Intern",description="Responsibilities:\nBuild SQL pipeline\nRequired Qualifications:\nSQL\nPreferred Skills:\nPython",skills="sql,python",location="India"),
            dict(id="other",title="Data Engineer",description="Responsibilities:\nBuild SQL pipeline\nRequired Qualifications:\nPython\nPreferred Skills:\nSQL",skills="sql,python",location="India")])
        result = rank_by_resume(df,"Skills:\nSQL\nProjects:\nSQL pipeline",resume_skills={"sql"})
        self.assertEqual(result.iloc[0].id,"intern")
        self.assertEqual(result.iloc[1].match_explanation["missing_required"],["python"])
        self.assertIsNotNone(result.iloc[0].match_explanation["project_responsibility_relevance"])
        override = rank_by_resume(df,"Skills:\nSQL\nProjects:\nSQL pipeline",resume_skills=set())
        self.assertEqual(override.iloc[0].match_explanation["matched_skills"],[])


if __name__ == "__main__":
    unittest.main()
