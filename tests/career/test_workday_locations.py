"""Workday aggregate labels must be resolved before India filtering."""
from contextlib import closing, nullcontext
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import backend.config as config
import backend.collector as run
from backend.api import data
from backend.core.location import is_india_or_unknown, is_workday_location_placeholder, parse_country
from backend.core.storage import init_db, save_job
from backend.fetchers import workday
from tests.career.test_collection_refresh import _ImmediatePool

CFG = next(cfg for cfg in config.WORKDAY if cfg['company'] == 'fractal')
PATH = '/job/New-York/Senior-Consultant---Marketing-Analytics_SR-46751'


def listing():
    return dict(total=1, jobPostings=[dict(title='Senior Consultant - Marketing Analytics',
        locationsText='2 Locations', externalPath=PATH, bulletFields=['SR-46751'])])


def us_detail():
    return dict(jobPostingInfo=dict(jobReqId='SR-46751', location='New York',
        additionalLocations=['California'], country={'descriptor':'United States of America'},
        jobDescription='<p>Marketing analytics</p>'))


class WorkdayLocationTests(unittest.TestCase):
    def test_reported_fractal_posting_uses_detail_country(self):
        with patch.object(workday, '_post', return_value=listing()), patch.object(workday, '_get', return_value=us_detail()):
            result = workday.fetch_workday(CFG)
        self.assertEqual(result[0]['location'], 'New York; California, United States of America')
        self.assertFalse(is_india_or_unknown(result[0]['location']))
        self.assertEqual(result.status, 'ok')

    def test_india_secondary_options_are_kept_without_foreign_contamination(self):
        info = dict(location='Bengaluru', additionalLocations=['Mumbai','Gurgaon','New York'], country={'descriptor':'India'})
        location = workday.posting_location(info, '4 Locations', india_location_names=CFG['india_location_names'])
        self.assertEqual(location, 'Bengaluru; Mumbai; Gurgaon, India')
        self.assertEqual(parse_country(location), 'India')
        info['country'] = {'descriptor':'United States of America'}
        info['location'] = 'New York'
        self.assertEqual(workday.posting_location(info, india_location_names=CFG['india_location_names']), 'Mumbai; Gurgaon, India')

    def test_aggregate_location_is_resolved_even_without_description_enrichment(self):
        cfg = {key:value for key,value in CFG.items() if key != 'fetch_details'}
        with patch.object(workday, '_post', return_value=listing()), patch.object(workday, '_get', return_value=us_detail()) as detail:
            result = workday.fetch_workday(cfg)
        detail.assert_called_once()
        self.assertFalse(is_india_or_unknown(result[0]['location']))

    def test_unresolved_or_wrong_detail_is_partial_and_not_a_saved_unknown(self):
        for detail in [{}, {'jobPostingInfo': {'jobReqId':'wrong'}}]:
            with self.subTest(detail=detail), patch.object(workday, '_post', return_value=listing()), patch.object(workday, '_get', return_value=detail):
                result = workday.fetch_workday(CFG)
                self.assertEqual(result, [])
                self.assertEqual(result.status, 'partial')
        self.assertTrue(is_workday_location_placeholder('2 Locations'))
        self.assertFalse(is_workday_location_placeholder('2 Locations, India'))
        self.assertFalse(is_workday_location_placeholder('Location to be confirmed'))

    def test_full_description_is_not_truncated_by_detail_wrapper(self):
        detail = us_detail()
        detail['jobPostingInfo']['jobDescription'] = '<p>' + 'Background '*900 + '</p><p>5 years of experience required</p>'
        with patch.object(workday, '_get', return_value=detail):
            text = workday.fetch_job_detail('https://example.com','example','Careers','/job/1','https://example.com')
        self.assertTrue(text.endswith('5 years of experience required'))
        self.assertGreater(len(text), 6000)

    def test_legacy_placeholder_is_hidden_without_deleting_tracking_history(self):
        with tempfile.TemporaryDirectory() as folder:
            db = str(Path(folder)/'jobs.db')
            with closing(sqlite3.connect(db)) as conn:
                init_db(conn)
                for sid,location in [('placeholder','2 Locations'),('india','Bengaluru, India'),('unknown','Location to be confirmed'),('us','New York; California, United States of America')]:
                    save_job(conn,sid,dict(company='fractal',title='Analyst',url='https://example.com/'+sid,location=location), 'workday')
                conn.execute("UPDATE jobs SET tracking_status='applied', notes='Keep this' WHERE id='placeholder'")
                conn.commit()
            with patch.object(data,'DB_PATH',db):
                self.assertEqual(set(data._load_jobs_df()['id']), {'india','unknown'})
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute("SELECT tracking_status,notes FROM jobs WHERE id='placeholder'").fetchone(), ('applied','Keep this'))

    def test_collection_corrects_existing_foreign_location_before_country_gate(self):
        conn = sqlite3.connect(':memory:')
        init_db(conn)
        job = dict(company='fractal',source_id='SR-46751',title='Analyst',location='2 Locations',url='https://example.com/1',description='SQL')
        save_job(conn,'fractal:SR-46751',job,'workday')
        conn.execute("UPDATE jobs SET tracking_status='applied',notes='Keep',dismissed=1")
        conn.commit()
        captured = []
        def inspect(deadline):
            captured.append(conn.execute('SELECT location,tracking_status,notes,dismissed FROM jobs').fetchone())
            return []
        with patch.object(run,'PLATFORMS',[('workday',lambda deadline:[dict(job,location='New York, United States')]),('inspect',inspect)]), \
             patch.object(run,'ThreadPoolExecutor',_ImmediatePool), patch.object(run.sqlite3,'connect',return_value=conn), \
             patch.object(run,'process_backlog'), patch.object(run,'cleanup_old',return_value=0), patch.dict('os.environ',{'JOB_INTEL_OFFLINE':'0'}):
            run._run()
        self.assertEqual(captured,[('New York, United States','applied','Keep',1)])


if __name__ == '__main__':
    unittest.main()
