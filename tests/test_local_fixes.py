"""Personal-use regressions: parsing, retention, duplicate evidence and cache recovery."""
from contextlib import ExitStack, nullcontext
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import torch

import run
from core import matcher, match_sections
from core.dedup import canonical_job_url, dedup_key
from core.experience import experience_requirements
from core.storage import cleanup_old, init_db, save_job
from tests.test_collection_refresh import _ImmediatePool
from tests.test_resume_matching import Model


class ExperienceFieldTests(unittest.TestCase):
    def test_bare_ranges_and_required_preferred_separation(self):
        for text, expected in [
            ("Experience: 0-2 years", (0, None)),
            ("Experience:\n1+ years", (1, None)),
            ("Work Experience: 5+ yrs", (5, None)),
            ("Required experience: 0–2 years", (0, None)),
            ("Experience Required: 1+ years", (1, None)),
            ("Experience Preferred: 2+ years", (None, 2)),
            ("Experience: 2 to 3+ years", (2, None)),
            ("Experience: 0.5 years", (0.5, None)),
            ("Experience: 0 years\nPreferred experience: 2+ years", (0, 2)),
            ("Experience: 3+ years preferred", (None, 3)),
            ("Preferred Experience:\n2 years", (None, 2)),
            ("Experience: Unknown", (None, None)),
            ("Experience: Working with SQL\nContract: 2 years", (None, None)),
            ("Experience: 2 years contract", (None, None)),
            ("Degree: 4 years", (None, None)),
            ("<h3>Experience:</h3><p>1&ndash;3 years</p>", (1, None)),
        ]:
            with self.subTest(text=text):
                self.assertEqual(experience_requirements(text), expected)

    def test_common_headings_preserve_preference_boundary(self):
        for heading in ["Qualifications", "Who you are", "Key Requirements",
                        "What we're looking for", "What we’re looking for", "Skills required"]:
            with self.subTest(heading=heading):
                _, required, preferred, _ = match_sections.weighted_skills(
                    heading + ":\nSQL\nPreferred Skills:\nPython", {"sql", "python"}, {"sql"})
                self.assertEqual(required, {"sql"})
                self.assertEqual(preferred, {"python"})
        self.assertEqual(match_sections.sections("We explain qualifications during onboarding.")["required"], "")

    def test_experience_subheading_inherits_required_or_preferred_context(self):
        text = "Preferred Qualifications:\nExperience: 2+ years\nRequired Qualifications:\nExperience: 0-2 years"
        self.assertEqual(experience_requirements(text), (0, 2))
        self.assertEqual(experience_requirements("Preferred Qualifications:\nWork Experience: 3 years"), (None, 3))
        self.assertEqual(experience_requirements("Preferred Qualifications:\nSQL\nRequired Experience: 1+ years"), (1, None))

    def test_cached_skills_follow_text_and_custom_vocabulary(self):
        desc = "Qualifications:\nSQL and DuckDB"
        match_sections._job_skill_sections.cache_clear()
        first = match_sections.weighted_skills(desc, {"sql"}, {"sql"})
        first[1].clear()  # Returned sets must not mutate the cached features.
        second = match_sections.weighted_skills(desc, {"sql"}, {"sql"})
        self.assertEqual(second[1], {"sql"})
        self.assertEqual(match_sections._job_skill_sections.cache_info().hits, 1)
        self.assertIn("duckdb", match_sections.weighted_skills(desc, {"sql"}, {"duckdb"})[1])
        self.assertEqual(match_sections.weighted_skills("Qualifications:\nPython", set(), {"sql"})[1], {"python"})

    def test_experience_cache_follows_description_and_title_changes(self):
        experience_requirements.cache_clear()
        self.assertEqual(experience_requirements("Experience: 0-2 years", "Analyst"), (0, None))
        self.assertEqual(experience_requirements("Experience: 0-2 years", "Analyst"), (0, None))
        self.assertEqual(experience_requirements.cache_info().hits, 1)
        self.assertEqual(experience_requirements("Experience: 3+ years", "Analyst"), (3, None))
        self.assertEqual(experience_requirements("Experience: 0-2 years", "Analyst - 4+ years"), (4, None))


class RetentionTests(unittest.TestCase):
    def test_last_observation_retains_identity_and_dismissal(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        init_db(conn)
        now = 2_000_000_000
        old = now - 400 * 86400
        for jid, last in [("live", now), ("stale", old), ("legacy", None),
                          ("boundary", now - 365 * 86400)]:
            save_job(conn, jid, dict(company="example", title="Analyst", location="India",
                                    url="https://example.com/" + jid, description="SQL"), "fixture")
            conn.execute("UPDATE jobs SET first_seen=?, last_seen=?, dismissed=1 WHERE id=?", (old, last, jid))
        with patch("core.storage.time.time", return_value=now):
            self.assertEqual(cleanup_old(conn), 2)
        self.assertEqual(conn.execute("SELECT id,dismissed FROM jobs ORDER BY id").fetchall(),
                         [("boundary", 1), ("live", 1)])


class DuplicateEvidenceTests(unittest.TestCase):
    def test_full_description_and_requisition_identity(self):
        intro = "About our company. " * 60
        self.assertNotEqual(dedup_key("example", "Analyst", "Delhi", intro + "Finance team"),
                            dedup_key("example", "Analyst", "Delhi", intro + "Marketing team"))
        self.assertNotEqual(dedup_key("example", "Analyst", "Delhi", intro, "https://example.com/jobs/1"),
                            dedup_key("example", "Analyst", "Delhi", intro, "https://example.com/jobs/2"))
        self.assertEqual(canonical_job_url("https://EXAMPLE.com/job/?gh_jid=123&utm_source=email"),
                         canonical_job_url("https://example.com/job?gh_jid=123"))
        self.assertNotEqual(canonical_job_url("https://example.com/job?gh_jid=123"),
                            canonical_job_url("https://example.com/job?gh_jid=456"))
        self.assertNotEqual(canonical_job_url("https://example.com/#/job/1"),
                            canonical_job_url("https://example.com/#/job/2"))

    def test_collection_keeps_ambiguous_jobs_and_refreshes_confirmed_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "jobs.db")
            base = dict(company="example", title="Analyst", location="Delhi, India",
                        url="https://example.com/jobs/1", description="Company background " * 60 + "Finance SQL")
            conn = sqlite3.connect(path); init_db(conn)
            save_job(conn, "example:old", base, "fixture")
            conn.execute("UPDATE jobs SET dismissed=1, first_seen=1,last_seen=1"); conn.commit(); conn.close()
            jobs = [dict(base, source_id="alias", url=base["url"] + "?utm_source=other"),
                    dict(base, source_id="different-id", url="https://example.com/jobs/2"),
                    dict(base, source_id="different-team", description=base["description"] + "Marketing"),
                    dict(base, source_id="missing-text-a", description=""),
                    dict(base, source_id="missing-text-b", description="")]
            with patch.object(run, "DB_PATH", path), patch.object(run, "PLATFORMS", [("fixture", lambda deadline: jobs)]), \
                 patch.object(run, "collection_lock", return_value=nullcontext()), \
                 patch.object(run, "ThreadPoolExecutor", _ImmediatePool), patch.object(run, "process_backlog"), \
                 patch.object(run, "cleanup_old", return_value=0), patch.dict(run.os.environ, {"JOB_INTEL_OFFLINE": "0"}):
                run.run()
            conn = sqlite3.connect(path)
            try:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 5)
                dismissed, first, last = conn.execute("SELECT dismissed,first_seen,last_seen FROM jobs WHERE id='example:old'").fetchone()
                self.assertEqual((dismissed, first), (1, 1))
                self.assertGreater(last, 1)
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM jobs WHERE id='example:alias'").fetchone()[0], 0)
            finally:
                conn.close()


class EmbeddingCacheTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(matcher, "get_model", return_value=Model()))
        self.identity = self.stack.enter_context(patch.object(matcher, "model_cache_identity", return_value="model-a"))
        self.frame = pd.DataFrame([dict(id="a",title="Analyst",description="Qualifications:\nSQL")])

    def test_current_dimension_method_is_used_when_available(self):
        model = matcher.get_model()
        with patch.object(model, "get_embedding_dimension", return_value=3, create=True) as current, \
             patch.object(model, "get_sentence_embedding_dimension", side_effect=AssertionError("Deprecated method")):
            self.assertEqual(matcher.embed_jobs_incremental(self.frame)[2], 1)
            current.assert_called_once()

    def test_model_and_section_changes_invalidate_both_caches(self):
        _, cache, _ = matcher.embed_jobs_incremental(self.frame)
        key = matcher.resume_embedding_key("Skills:\nSQL")
        self.assertEqual(matcher.embed_jobs_incremental(self.frame, cache)[2], 0)
        self.identity.return_value = "model-b"
        self.assertEqual(matcher.embed_jobs_incremental(self.frame, cache)[2], 1)
        self.assertNotEqual(matcher.resume_embedding_key("Skills:\nSQL"), key)
        self.identity.return_value = "model-a"
        with patch.object(matcher, "SECTION_VERSION", "new-parser"):
            self.assertEqual(matcher.embed_jobs_incremental(self.frame, cache)[2], 1)
            self.assertNotEqual(matcher.resume_embedding_key("Skills:\nSQL"), key)

    def test_malformed_and_nonfinite_entries_rebuild(self):
        _, cache, _ = matcher.embed_jobs_incremental(self.frame)
        content_hash = cache["a"][0]
        for value in [None, (content_hash,), (content_hash, "not a tensor"),
                      (content_hash, torch.ones(3)), (content_hash, torch.ones(2, 9)),
                      (content_hash, torch.ones(2, 3, dtype=torch.int64)),
                      (content_hash, torch.full((2, 3), float("nan")))]:
            with self.subTest(value=str(value)):
                embeddings, _, count = matcher.embed_jobs_incremental(self.frame, {"a": value})
                self.assertEqual(count, 1)
                self.assertTrue(torch.isfinite(embeddings).all())

    def test_atomic_cache_write_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jobs.pt"
            _, cache, _ = matcher.embed_jobs_incremental(self.frame)
            matcher.save_embedding_cache(cache, path)
            previous = path.read_bytes()
            def interrupted(cache, stream):
                stream.write(b"partial")
                raise OSError("Disk full")
            with patch.object(matcher.torch, "save", side_effect=interrupted):
                with self.assertRaises(OSError):
                    matcher.save_embedding_cache({}, path)
            self.assertEqual(path.read_bytes(), previous)
            self.assertEqual(set(matcher.load_embedding_cache(path)), {"a"})
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])
