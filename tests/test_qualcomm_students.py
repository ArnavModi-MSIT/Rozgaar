import json
import sqlite3
import unittest
from unittest.mock import patch

from core.storage import init_db, save_job, refresh_qualcomm_student
from fetchers import qualcomm_students as source


def row(i):
    return {'id': i, 'name': 'Interim Engineering Intern_2027_SW', 'locations': ['Hyderabad, India']}


class QualcommStudentTests(unittest.TestCase):
    def test_filters_pagination_and_full_descriptions(self):
        pages = [{'data': {'count': 11, 'positions': [row(i) for i in range(1, 11)]}},
                 {'data': {'count': 11, 'positions': [row(11)]}}]
        with patch.object(source.eightfold, '_get', side_effect=pages) as get, patch.object(source, '_description', return_value='Currently enrolled in BTech'), patch.object(source.time, 'sleep'):
            result = source.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result), 11)
        self.assertEqual([c.args[1]['start'] for c in get.call_args_list], [0, 10])
        for call in get.call_args_list:
            params = call.args[1]
            self.assertEqual(params['filter_seniority'], 'Intern')
            self.assertEqual(params['filter_include_remote'], '0')
            self.assertEqual(params['filter_include_relocation'], '0')
            self.assertEqual(params['location'], 'india')
            self.assertEqual(params['sort_by'], 'distance')
        self.assertEqual(result[0]['description'], 'Currently enrolled in BTech')

    def test_structured_description_retains_qualifications(self):
        data = {'@type': 'JobPosting', 'description': '<p>Software internship</p><h2>Qualifications</h2><p>Currently pursuing BTech</p>'}
        html = '<script type="application/ld+json">' + json.dumps(data) + '</script>'
        with patch.object(source, 'get_text', return_value=html):
            description = source._description({'url': 'https://careers.qualcomm.com/careers/job/1'}, None)
        self.assertIn('Currently pursuing BTech', description)

    def test_empty_is_success_but_failure_is_not_empty(self):
        with patch.object(source.eightfold, '_get', return_value={'data': {'count': 0, 'positions': []}}):
            self.assertEqual(source.collect().status, 'ok')
        with patch.object(source.eightfold, '_get', return_value=None):
            with self.assertRaises(RuntimeError):
                source.collect()

    def test_missing_description_and_interrupted_page_are_partial(self):
        with patch.object(source.eightfold, '_get', side_effect=[{'data': {'count': 11, 'positions': [row(1)]}}, None]), patch.object(source, '_description', return_value=''), patch.object(source.time, 'sleep'):
            result = source.collect()
        self.assertEqual(result.status, 'partial')
        self.assertIn('description unavailable', result.error)
        self.assertIn('received 1 of 11', result.error)

    def test_enrichment_preserves_dismissal_and_first_seen(self):
        conn = sqlite3.connect(':memory:')
        init_db(conn)
        job = {'company': 'qualcomm', 'source_id': '1', 'title': 'Intern_2027', 'location': 'India', 'url': 'https://careers.qualcomm.com/careers/job/1', 'description': 'Department: Software'}
        save_job(conn, 'qualcomm:1', job, 'eightfold')
        conn.execute("UPDATE jobs SET first_seen=123, dismissed=1, category='Other', skills='sql', experience_years=-1 WHERE id='qualcomm:1'")
        full = dict(job, description='Currently pursuing BTech. Required: Python.')
        self.assertTrue(refresh_qualcomm_student(conn, 'qualcomm:1', full))
        self.assertEqual(conn.execute("SELECT first_seen,dismissed,category,skills,experience_years,source FROM jobs WHERE id='qualcomm:1'").fetchone(), (123, 1, None, None, None, 'qualcomm_students'))
        self.assertFalse(refresh_qualcomm_student(conn, 'qualcomm:1', full))
        self.assertFalse(refresh_qualcomm_student(conn, 'qualcomm:1', dict(job, description='')))
        conn.close()
