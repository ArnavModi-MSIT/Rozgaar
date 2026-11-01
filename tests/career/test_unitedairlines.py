import json
import time
import unittest
from unittest.mock import patch

from backend.fetchers import unitedairlines as source


def row(sid='GGN1', category='Digital Technology'):
    return dict(jobId=sid, title='Data Engineer', jobSeqNo=source.REFNUM + sid + 'EXTERNALENUSTALEO',
                country='India', location='Gurugram, Haryana, India', siteType='external', category=category,
                applyUrl='https://example.test/application', recruiterAssistantEmail='private@example.test')


def page(rows, total):
    return {'refineSearch': {'status': 200, 'totalHits': total, 'data': {'jobs': rows}}}


def detail(sid='GGN1', **overrides):
    data = dict(refNum=source.REFNUM, jobId=sid, title='Data Engineer', country='India', siteType='external',
                externalDescription='<p>Responsibilities: ' + 'Python SQL ' * 900 + '</p>',
                qualifications='<p>Required: 0-1 years of experience. Last qualification.</p>',
                intDescription='Internal HR data', recruiterAssistantEmail='private@example.test')
    data.update(overrides)
    return '<script>phApp.ddo = ' + json.dumps({'jobDetail': {'status': 200, 'data': {'job': data}}}) + ';</script>'


class UnitedAirlinesTests(unittest.TestCase):
    cfg = {'company': 'unitedairlines'}

    def test_multiple_pages_country_scope_and_corporate_roles(self):
        with patch.object(source, 'post_json', side_effect=[page([row()], 2), page([row('GGN2', 'Corporate')], 2)]) as post, \
             patch.object(source, 'get_text', side_effect=[detail(), detail('GGN2')]), \
             patch.object(source.time, 'sleep'):
            jobs = source.fetch(self.cfg)
        self.assertEqual(jobs.status, 'ok')
        self.assertEqual([j['source_id'] for j in jobs], ['GGN1', 'GGN2'])
        self.assertEqual([c.kwargs['json']['from'] for c in post.call_args_list], [0, 10])
        for call in post.call_args_list:
            self.assertEqual(call.kwargs['json']['selected_fields'], {'country': ['India']})
        self.assertGreater(len(jobs[0]['description']), 6000)
        self.assertIn('Last qualification.', jobs[0]['description'])
        self.assertNotIn('Internal HR data', jobs[0]['description'])
        self.assertNotIn('recruiterAssistantEmail', jobs[0])
        self.assertIn('/us/en/job/GGN1/', jobs[0]['url'])
        self.assertNotIn('application', jobs[0]['url'])

    def test_listing_employer_country_and_requisition_identity(self):
        for field, value in [('country', 'United States'), ('country', 'Indiana'),
                             ('jobSeqNo', 'OTHERGGN1'), ('refNum', 'OTHER'),
                             ('jobId', '../GGN1'), ('siteType', 'internal'), ('title', '')]:
            record = row(); record[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                source._listing(record)

    def test_detail_identity_and_missing_body_never_use_search_teaser(self):
        job = source._listing(row())
        for overrides in [dict(jobId='GGN2'), dict(country='USA'), dict(title='Other job'),
                          dict(refNum='OTHER'), dict(siteType='internal'),
                          dict(externalDescription='', description='')]:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                source._description(detail(**overrides), job)
        with self.assertRaises(ValueError):
            source._description('<html>Job no longer available</html>', job)

    def test_later_listing_failure_or_repeated_page_keeps_partial(self):
        for second in [None, page([row()], 2), {'refineSearch': {'data': ['invalid']}}]:
            with self.subTest(second=second), \
                 patch.object(source, 'post_json', side_effect=[page([row()], 2), second]), \
                 patch.object(source, 'get_text', return_value=detail()), patch.object(source.time, 'sleep'):
                jobs = source.fetch(self.cfg)
            self.assertEqual(jobs.status, 'partial')
            self.assertEqual(len(jobs), 1)
            self.assertTrue(jobs[0]['description'])

    def test_missing_description_is_partial_and_failed_first_page_is_not_zero(self):
        with patch.object(source, 'post_json', return_value=page([row()], 1)), patch.object(source, 'get_text', return_value=None):
            jobs = source.fetch(self.cfg)
        self.assertEqual(jobs.status, 'partial')
        self.assertEqual(jobs[0]['description'], '')
        with patch.object(source, 'post_json', return_value=None), self.assertRaises(RuntimeError):
            source.fetch(self.cfg)
        with patch.object(source, 'post_json', return_value=page([], 0)):
            self.assertEqual(source.fetch(self.cfg).status, 'ok')

    def test_deadline_prevents_first_network_request(self):
        with patch.object(source, 'post_json') as post, self.assertRaises(RuntimeError):
            source.fetch(self.cfg, time.monotonic() - 1)
        post.assert_not_called()
