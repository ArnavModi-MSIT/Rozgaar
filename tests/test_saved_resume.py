"""Saved-resume lifecycle uses synthetic text, a fake model and an isolated DB."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import data, main
from core import matcher, resume_cache
from tests.test_resume_matching import Model


def empty_state():
    return dict(key=None, text="", skills=set(), scores={}, explanations={}, pool_key=None,
                filename=None, embedding=None, embedding_key=None)


class SavedResumeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.cache_path = root / "saved_resume.json"
        self.stack.enter_context(patch.object(data, "DB_PATH", str(root / "jobs.db")))
        self.stack.enter_context(patch.object(data, "_initialized_db_paths", set()))
        self.stack.enter_context(patch.object(data, "_jobs_cache", dict(df=None, loaded_at=0)))
        self.stack.enter_context(patch.object(data, "_embedding_cache", None))
        self.stack.enter_context(patch.object(data, "_resume", empty_state()))
        self.stack.enter_context(patch.object(resume_cache, "CACHE_PATH", self.cache_path))
        self.model = Model()
        self.stack.enter_context(patch.object(matcher, "get_model", return_value=self.model))
        self.stack.enter_context(patch.object(data, "load_embedding_cache", side_effect=lambda: matcher.load_embedding_cache(root / "jobs.pt")))
        self.stack.enter_context(patch.object(data, "save_embedding_cache", side_effect=lambda cache: matcher.save_embedding_cache(cache, str(root / "jobs.pt"))))
        self.parse = self.stack.enter_context(patch.object(main, "extract_text", wraps=main.extract_text))
        self.encode = self.stack.enter_context(patch.object(data, "embed_resume", wraps=data.embed_resume))
        self.client = self.stack.enter_context(TestClient(main.app))
        self.add_job("a")

    def add_job(self, sid):
        conn = data.connect()
        try:
            conn.execute("INSERT INTO jobs(id,company,title,location,url,description,source,first_seen,last_seen,skills) VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (sid, "example", "Data Engineer Intern", "India", "https://example.com/" + sid,
                          "Required Qualifications:\nSQL\nResponsibilities:\nBuild a SQL pipeline", "standard", 100, 100, "sql"))
            conn.commit()
        finally:
            conn.close()
        data.invalidate_jobs()

    def upload(self, text="Skills:\nSQL\nProjects:\nBuilt a SQL pipeline", save=True, name="sample.txt"):
        return self.client.post("/api/resume", files={"file": (name, text.encode(), "text/plain")},
                                data={"save_for_later": str(save).lower()})

    def test_global_vocabulary_edits_preserve_manual_and_empty_overrides(self):
        for manual in [["python", "power bi"], []]:
            with self.subTest(manual=manual):
                self.assertEqual(self.upload().status_code, 200)
                self.assertEqual(self.client.put("/api/resume/skills", json={"skills": manual}).status_code, 200)
                self.assertEqual(self.client.post("/api/custom-skills", json={"skill": "pipeline"}).status_code, 200)
                self.assertEqual(self.client.get("/api/resume").json()["skills"], sorted(manual))
                self.assertEqual(self.client.delete("/api/custom-skills/pipeline").status_code, 200)
                self.assertEqual(self.client.get("/api/resume").json()["skills"], sorted(manual))
                self.assertEqual(self.client.post("/api/resume/previous").status_code, 200)
                self.assertEqual(self.client.get("/api/resume").json()["skills"], sorted(manual))

    def test_vocabulary_edits_refresh_auto_skills_without_reembedding_resume(self):
        self.assertEqual(self.upload().status_code, 200)
        initial = self.encode.call_count
        self.client.post("/api/custom-skills", json={"skill": "pipeline"})
        self.assertIn("pipeline", self.client.get("/api/resume").json()["skills"])
        with patch.object(data, "rescore", wraps=data.rescore) as rescore:
            response = self.client.post("/api/custom-skills", json={"skill": "pipeline"})
            self.assertFalse(response.json()["added"])
            self.client.delete("/api/custom-skills/does-not-exist")
            rescore.assert_not_called()
        self.client.delete("/api/custom-skills/pipeline")
        self.assertNotIn("pipeline", self.client.get("/api/resume").json()["skills"])
        self.assertEqual(self.encode.call_count, initial)

    def test_job_cache_write_failure_does_not_reject_resume(self):
        with patch.object(data, "save_embedding_cache", side_effect=OSError("Read-only cache")), self.assertLogs("jobbot.api", level="WARNING"):
            response = self.upload(save=False)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["scored"], 1)

    def test_list_and_detail_share_one_pool_hash_until_jobs_reload(self):
        self.assertEqual(self.upload().status_code, 200)
        data.invalidate_jobs()
        with patch.object(data, "compute_job_pool_key", wraps=data.compute_job_pool_key) as fingerprint:
            self.client.get("/api/jobs")
            self.client.get("/api/jobs/a")
            self.client.get("/api/jobs")
            self.assertEqual(fingerprint.call_count, 1)
            self.add_job("b")
            jobs = self.client.get("/api/jobs").json()["jobs"]
            self.assertEqual(len(jobs), 2)
            self.assertEqual(fingerprint.call_count, 2)
            self.assertEqual(set(data.resume_state()["scores"]), {"a", "b"})

    def test_failed_vocabulary_rescore_retains_active_manual_corrections(self):
        self.assertEqual(self.upload().status_code, 200)
        self.client.put("/api/resume/skills", json={"skills": ["python"]})
        with patch.object(data, "rank_by_resume", side_effect=RuntimeError("Synthetic scoring failure")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/custom-skills", json={"skill": "pipeline"})
        self.assertEqual(self.client.get("/api/resume").json()["skills"], ["python"])

    def test_restart_reuses_parsing_and_embedding_with_equal_scores(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(self.cache_path.exists())
        before = self.client.get("/api/jobs").json()["jobs"]
        self.assertEqual(self.parse.call_count, 1)
        self.assertEqual(self.encode.call_count, 1)
        # Simulate a new backend process; only local disk files survive.
        data.clear_resume(); data._embedding_cache = None
        state = self.client.get("/api/resume").json()
        self.assertFalse(state["loaded"])
        self.assertEqual(state["saved_resume"]["filename"], "sample.txt")
        response = self.client.post("/api/resume/previous")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["reused_text"])
        self.assertTrue(response.json()["reused_embedding"])
        self.assertEqual(self.parse.call_count, 1)
        self.assertEqual(self.encode.call_count, 1)
        self.assertEqual(self.client.get("/api/jobs").json()["jobs"], before)

    def test_identical_bytes_skip_parsing_and_changed_resume_rebuilds(self):
        self.assertEqual(self.upload().status_code, 200)
        self.assertTrue(self.upload(name="renamed.txt").json()["reused_text"])
        self.assertEqual(self.parse.call_count, 1)
        self.assertEqual(self.encode.call_count, 1)
        response = self.upload("Skills:\nPython\nProjects:\nPython service")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["reused_text"])
        self.assertEqual(self.parse.call_count, 2)
        self.assertEqual(self.encode.call_count, 2)

    def test_new_jobs_are_scored_and_skill_overrides_reuse_resume_embedding(self):
        self.assertEqual(self.upload().status_code, 200)
        self.assertEqual(self.client.put("/api/resume/skills", json={"skills": ["sql", "python"]}).status_code, 200)
        self.add_job("b")
        jobs = self.client.get("/api/jobs").json()["jobs"]
        self.assertEqual({j["id"] for j in jobs}, {"a", "b"})
        self.assertTrue(all(j["match_pct"] is not None for j in jobs))
        data.clear_resume()
        response = self.client.post("/api/resume/previous")
        self.assertEqual(response.json()["skills"], ["python", "sql"])
        self.assertEqual(self.encode.call_count, 1)

    def test_opt_out_and_delete_saved_copy(self):
        self.assertEqual(self.upload(save=False).status_code, 200)
        self.assertFalse(self.cache_path.exists())
        self.assertEqual(self.upload().status_code, 200)
        self.assertEqual(self.client.delete("/api/resume/saved").status_code, 200)
        self.assertFalse(self.cache_path.exists())
        self.assertTrue(self.client.get("/api/resume").json()["loaded"])
        self.assertEqual(self.client.post("/api/resume/previous").status_code, 404)

    def test_corrupt_cache_is_miss_and_bad_embedding_is_recomputed(self):
        self.cache_path.write_text("broken", encoding="utf-8")
        self.assertIsNone(resume_cache.load())
        self.assertEqual(self.client.post("/api/resume/previous").status_code, 404)
        self.assertEqual(self.upload().status_code, 200)
        record = json.loads(self.cache_path.read_text(encoding="utf-8"))
        record["embedding"] = [[1], [2, 3]]
        self.cache_path.write_text(json.dumps(record), encoding="utf-8")
        data.clear_resume()
        self.assertEqual(self.client.post("/api/resume/previous").status_code, 200)
        self.assertEqual(self.parse.call_count, 1)
        self.assertEqual(self.encode.call_count, 2)

    def test_changed_embedding_signature_rebuilds_only_resume_vector(self):
        self.assertEqual(self.upload().status_code, 200)
        record = json.loads(self.cache_path.read_text(encoding="utf-8"))
        record["embedding_key"] = "old-version"
        self.cache_path.write_text(json.dumps(record), encoding="utf-8")
        data.clear_resume()
        response = self.client.post("/api/resume/previous")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["reused_embedding"])
        self.assertEqual(self.parse.call_count, 1)
        self.assertEqual(self.encode.call_count, 2)

    def test_wrong_vector_dimension_is_rebuilt_not_claimed_as_reused(self):
        self.assertEqual(self.upload().status_code, 200)
        record = json.loads(self.cache_path.read_text(encoding="utf-8"))
        record["embedding"] = [[1.0], [1.0]]
        self.cache_path.write_text(json.dumps(record), encoding="utf-8")
        data.clear_resume()
        response = self.client.post("/api/resume/previous")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["reused_embedding"])
        self.assertEqual(self.encode.call_count, 2)

    def test_invalid_upload_preserves_current_and_saved_resume(self):
        self.assertEqual(self.upload().status_code, 200)
        saved = self.cache_path.read_bytes()
        key = data.resume_state()["key"]
        self.assertEqual(self.upload(" ").status_code, 400)
        self.assertEqual(self.cache_path.read_bytes(), saved)
        self.assertEqual(data.resume_state()["key"], key)

    def test_atomic_failed_save_preserves_existing_copy(self):
        self.assertEqual(self.upload().status_code, 200)
        saved = self.cache_path.read_bytes()
        with patch.object(resume_cache.os, "replace", side_effect=OSError("Disk full")), self.assertLogs("jobbot.api", level="WARNING"):
            response = self.upload("Skills:\nPython\nProjects:\nPython pipeline")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(response.json()["save_warning"])
        self.assertEqual(self.cache_path.read_bytes(), saved)
        self.assertEqual(list(self.cache_path.parent.glob("saved_resume.*.tmp")), [])

    def test_saved_json_contains_no_original_file_or_executable_tensor(self):
        self.assertEqual(self.upload(name="C:\\fakepath\\sample.txt").status_code, 200)
        record = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.assertEqual(record["filename"], "sample.txt")
        self.assertIsInstance(record["embedding"], list)
        self.assertNotIn("content", record)
        self.assertNotIn("original_file", record)
