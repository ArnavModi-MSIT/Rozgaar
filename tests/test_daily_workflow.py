"""Local tracker, lifecycle, health and evaluation checks on synthetic data only."""
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from api import data
from core import matcher
from core.source_health import dashboard, record_company_run
from core.storage import init_db, mark_observed, cleanup_old, update_job_state
from fetchers.result import CollectionResult
from fetchers import standard
from scripts.evaluate_matcher import evaluate, bm25_order, ranking_metrics
from tests import test_saved_resume as fixtures


class DailyWorkflowTests(unittest.TestCase):
    setUp = fixtures.SavedResumeTests.setUp
    add_job = fixtures.SavedResumeTests.add_job
    upload = fixtures.SavedResumeTests.upload

    def test_save_apply_notes_survive_connections_and_bypass_discovery_filters(self):
        self.assertEqual(self.client.put('/api/jobs/a/state', json={'tracking_status': 'saved', 'notes': 'Apply after class'}).status_code, 200)
        response = self.client.get('/api/tracker?view=saved').json()
        self.assertEqual(response['total'], 1)
        self.assertEqual(response['jobs'][0]['notes'], 'Apply after class')
        self.assertIsNotNone(response['jobs'][0]['saved_at'])
        self.client.post('/api/jobs/a/dismiss')
        self.assertEqual(self.client.get('/api/jobs').json()['jobs'], [])
        self.assertEqual(self.client.get('/api/tracker?view=saved').json()['total'], 1)
        self.client.put('/api/jobs/a/state', json={'tracking_status': 'applied'})
        self.assertEqual(self.client.get('/api/tracker?view=applied').json()['jobs'][0]['notes'], 'Apply after class')
        conn = data.connect()
        try:
            init_db(conn)  # Idempotent migration preserves all user state.
            self.assertEqual(conn.execute('SELECT tracking_status, notes FROM jobs WHERE id=?', ('a',)).fetchone(), ('applied', 'Apply after class'))
        finally:
            conn.close()

    def test_bulk_undo_restores_real_rows_only_and_validates_input(self):
        response = self.client.post('/api/jobs/dismiss-bulk', json={'ids': ['a', 'a', 'missing']})
        self.assertEqual(response.json()['dismissed'], 1)
        self.assertEqual(self.client.get('/api/tracker?view=removed').json()['total'], 1)
        self.assertEqual(self.client.post('/api/restore', json={'ids': ['a', 'a', 'missing']}).json()['restored'], 1)
        self.assertEqual(len(self.client.get('/api/jobs').json()['jobs']), 1)
        self.assertEqual(self.client.post('/api/jobs/missing/dismiss').status_code, 404)
        self.assertEqual(self.client.put('/api/jobs/a/state', json={'tracking_status': 'submitted'}).status_code, 422)
        self.assertEqual(self.client.put('/api/jobs/a/state', json={'notes': 'x'*4001}).status_code, 422)
        self.assertEqual(self.client.put('/api/jobs/missing/state', json={'notes': ''}).status_code, 404)
        self.assertEqual(self.client.get('/api/tracker?view=everything').status_code, 422)

    def test_closure_is_explicit_and_never_inferred_from_a_failed_or_empty_run(self):
        self.client.put('/api/jobs/a/state', json={'posting_status': 'closed'})
        conn = data.connect()
        try:
            mark_observed(conn, 'a', 1000)
            record_company_run(conn, 1, 'standard', status='failed', error='network unavailable')
            record_company_run(conn, 2, 'standard', [])
            conn.commit()
            row = conn.execute('SELECT posting_status, last_seen, status_evidence FROM jobs WHERE id=?', ('a',)).fetchone()
            self.assertEqual(row[:2], ('closed', 1000))
            self.assertIn('by you', row[2])
        finally:
            conn.close()
        self.assertEqual(self.client.get('/api/tracker?view=closed').json()['total'], 1)
        self.client.put('/api/jobs/a/state', json={'posting_status': 'open'})
        self.assertEqual(self.client.get('/api/tracker?view=closed').json()['total'], 0)

    def test_saved_applied_and_notes_are_protected_from_retention(self):
        for sid in ['b', 'c', 'd']:
            self.add_job(sid)
        conn = data.connect()
        try:
            update_job_state(conn, 'a', tracking_status='saved')
            update_job_state(conn, 'b', tracking_status='applied')
            update_job_state(conn, 'c', notes='Keep this reference')
            with patch('core.storage.time.time', return_value=400*86400):
                self.assertEqual(cleanup_old(conn), 1)
            self.assertEqual({r[0] for r in conn.execute('SELECT id FROM jobs')}, {'a','b','c'})
        finally:
            conn.close()

    def test_health_keeps_company_outcomes_distinct_and_legacy_coverage_unverified(self):
        jobs = CollectionResult([
            dict(company='example', location='Delhi, India', description=''),
            dict(company='example', location='Paris, France', description='Foreign JD'),
        ], status='partial', companies={'example': {'status':'partial','error':'detail failed'},
                                        'empty': {'status':'ok','error':''}})
        conn = data.connect()
        try:
            with patch('core.source_health.configured_company_sources', return_value={'example': {'standard'}, 'empty': {'standard'}}):
                record_company_run(conn, 1, 'standard', jobs, status='partial')
                conn.commit()
                report = dashboard(conn)
                by_company = {row['company']: row for row in report['companies']}
                self.assertEqual((by_company['example']['fetched'], by_company['example']['india_or_unknown'], by_company['example']['missing_descriptions']), (2,1,1))
                self.assertEqual(by_company['example']['status'], 'partial')
                self.assertEqual(by_company['empty']['status'], 'ok')
                record_company_run(conn, 2, 'standard', [], status='ok')
                conn.commit()
                self.assertTrue(all(row['status'] == 'unverified' for row in dashboard(conn)['companies']))
        finally:
            conn.close()
        self.assertEqual(self.client.get('/api/source-health').status_code, 200)

    def test_eligibility_is_lazy_but_available_on_detail_and_scores_are_unchanged(self):
        with patch.object(matcher, 'eligibility_checks', wraps=matcher.eligibility_checks) as checks:
            self.assertEqual(self.upload(save=False).status_code, 200)
            checks.assert_not_called()
            row = self.client.get('/api/jobs').json()['jobs'][0]
            self.assertEqual(row['match_explanation']['eligibility_checks'], [])
            detail = self.client.get('/api/jobs/a').json()
            self.assertGreater(len(detail['match_explanation']['eligibility_checks']), 0)
            checks.assert_not_called()  # API detail calls its own imported helper.
            frame = data.get_jobs_df()
            state = data.resume_state()
            expected = matcher.rank_by_resume(frame, state['text'], resume_skills=state['skills'])
            self.assertEqual(row['match_pct'], expected.iloc[0]['match_pct'])
            checks.assert_called_once()


class MigrationAndEvaluatorTests(unittest.TestCase):
    def test_standard_adapter_reports_board_success_and_failure_separately(self):
        def board(company):
            if company == 'broken':
                raise RuntimeError('Synthetic missing board')
            return [dict(company=company, description='SQL')]
        with patch.object(standard, 'fetch_greenhouse', side_effect=board), patch.object(standard.log, 'exception'):
            result = standard.collect(['working','broken'], [], [])
        self.assertEqual(result.status, 'partial')
        self.assertEqual(result.companies['working']['status'], 'ok')
        self.assertEqual(result.companies['broken']['status'], 'failed')

    def test_old_database_defaults_to_unknown_and_preserves_dismissal(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute('CREATE TABLE jobs(id TEXT PRIMARY KEY,company TEXT,title TEXT,location TEXT,url TEXT,description TEXT,source TEXT,score INTEGER,first_seen INTEGER,dismissed INTEGER DEFAULT 0)')
        conn.execute("INSERT INTO jobs(id,company,title,first_seen,dismissed) VALUES('old','example','Data',100,1)")
        init_db(conn); init_db(conn)
        self.assertEqual(conn.execute('SELECT posting_status,tracking_status,dismissed FROM jobs').fetchone(), ('unknown','none',1))

    def test_bm25_and_metrics_include_unmatched_rows_and_literal_query_operators(self):
        jobs = [{'id':'good','title':'Data analyst','description':'SQL dashboard','grade':2},
                {'id':'bad','title':'Chef','description':'Cooking','grade':0}]
        self.assertEqual(bm25_order(jobs, 'SQL OR " AND NOT dashboard')[0], 0)
        self.assertEqual(len(bm25_order(jobs, 'unmatchedword')), 2)
        self.assertEqual(ranking_metrics([0,2], 1)['precision_at_k'], 0)
        self.assertAlmostEqual(ranking_metrics([0,2], 1)['ndcg_at_k'], 0)
        report = evaluate({'resume_text':'SQL dashboard','jobs':jobs}, k=1, bm25_only=True)
        self.assertEqual(report['methods']['bm25']['precision_at_k'], 1)
        for invalid in [True, 3, '2']:
            with self.assertRaises(ValueError):
                evaluate({'resume_text':'SQL','jobs':[dict(jobs[0],grade=invalid)]})
        with self.assertRaises(ValueError):
            evaluate({'resume_text':'SQL','jobs':jobs}, k=0, bm25_only=True)


if __name__ == '__main__':
    unittest.main()
