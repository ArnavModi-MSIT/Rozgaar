"""Offline checks for launcher identity, collector locks, and API score state."""
from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd

import start
from api import data, main
from core.matcher import compute_job_pool_key
from core.run_lock import collection_lock
from core.storage import update_descriptions


def frame(description="SQL required"):
    return pd.DataFrame([dict(id="a",title="Data Engineer",company="example",location="India",url="https://example.com",source="standard",category="",skills="sql",experience_years=2.5,preferred_experience_years=-1,first_seen=pd.Timestamp("2026-10-07"),last_seen=pd.Timestamp("2026-10-07"),is_remote=False,is_ncr=False,is_india=True,description=description)])


class RuntimeReviewTests(unittest.TestCase):
    def test_collection_lock_rejects_overlap_and_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"collector.lock"
            with collection_lock(path):
                with self.assertRaisesRegex(RuntimeError,"already running"):
                    with collection_lock(path):
                        pass
            with collection_lock(path):
                pass

    def test_stale_backend_is_not_silently_reused(self):
        with patch.object(start,"ui_needs_build",return_value=False),patch.object(start,"api_ready",return_value=False),patch.object(start,"api_status",return_value="stale"),patch.object(start.subprocess,"Popen") as spawn:
            with self.assertRaisesRegex(RuntimeError,"older Job Intel"):
                start.main(["--no-scrape"])
            spawn.assert_not_called()

    def test_launcher_identity_requires_current_checkout_revision(self):
        expected={"root":"test","revision":"new"}
        @contextmanager
        def response(value):
            yield io.BytesIO(json.dumps(value).encode())
        with patch.object(start,"runtime_identity",return_value=expected),patch.object(start,"urlopen",side_effect=[response({"info":{"title":"Job Intel API"}}),response({**expected,"revision":"old"})]):
            self.assertEqual(start.api_status(),"stale")

    def test_failed_new_resume_preserves_previous_state(self):
        state=dict(key="old",text="old resume",skills={"sql"},scores={"a":75},explanations={"a":{}},pool_key="old")
        with patch.object(data,"_resume",state),patch.object(data,"rescore",side_effect=RuntimeError("model unavailable")):
            with self.assertRaises(RuntimeError):
                data.set_resume("new","new resume",{"python"})
            self.assertEqual(state["key"],"old")
            self.assertEqual(state["scores"],{"a":75})
            snapshot=data.resume_state();snapshot["skills"].clear()
            self.assertEqual(state["skills"],{"sql"})

    def test_changed_job_pool_rescores_before_list_payload(self):
        df=frame()
        state=dict(key="resume",text="SQL",skills={"sql"},scores={},explanations={},pool_key="old")
        def score(jobs,*args,**kwargs):
            result=jobs.copy();result["match_pct"]=80.0;result["match_explanation"]=[{"missing_required":[]}]*len(result)
            return result
        with patch.object(data,"_resume",state),patch.object(data,"_ensure_embeddings",return_value=None),patch.object(data,"rank_by_resume",side_effect=score) as rank:
            payload=data.job_list_payload(df)
            self.assertEqual(payload[0]["match_pct"],80)
            self.assertEqual(payload[0]["experience_years"],2.5)
            data.job_list_payload(df)
            self.assertEqual(rank.call_count,1)
            data.job_list_payload(frame("Python required"))
            self.assertEqual(rank.call_count,2)

    def test_refetch_resets_derived_fields_without_changing_user_state(self):
        import sqlite3
        conn=sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE jobs(id TEXT,description TEXT,skills TEXT,category TEXT,experience_years REAL,dismissed INTEGER)")
        conn.execute("INSERT INTO jobs VALUES('a','old','sql','data',-1,1)")
        update_descriptions(conn,[("a","3 years of Python experience")])
        self.assertEqual(conn.execute("SELECT skills,category,experience_years,dismissed FROM jobs").fetchone(),(None,None,None,1))
        update_descriptions(conn,[("a","")])
        self.assertEqual(conn.execute("SELECT description FROM jobs").fetchone()[0],"3 years of Python experience")
        conn.close()

    def test_browser_cross_origin_mutation_blocked_without_database_access(self):
        from starlette.requests import Request
        from starlette.responses import Response
        async def call_next(request):
            return Response(status_code=204)
        for origin,expected in [("https://example.com",403),("http://127.0.0.1:8000",204)]:
            request=Request({"type":"http","method":"POST","path":"/api/jobs/a/dismiss","headers":[(b"origin",origin.encode())]})
            coroutine=main.protect_local_mutations(request,call_next)
            try:
                coroutine.send(None)
                self.fail("Unexpected asynchronous I/O in origin guard")
            except StopIteration as completed:
                result=completed.value
            self.assertEqual(result.status_code,expected)
