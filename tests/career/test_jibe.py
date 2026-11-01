"""Synthetic public feeds: no live employer or applicant requests."""
import time
import unittest
from unittest.mock import patch

from backend.fetchers import jibe


def posting(sid='1', **extra):
    return {'data': dict(req_id=sid, slug=sid, title='Data Engineer', country='India',
                         city='Mumbai', client_code='medpace', tags2=['Epsilon'],
                         description='<p>Responsibilities</p><p>' + 'Python SQL ' * 800 + '</p>',
                         qualifications='<p>Qualifications: 0-1 years of experience</p>', **extra)}


class JibeTests(unittest.TestCase):
    cfg = dict(company='medpace', host='careers.medpace.com', client_code='medpace')

    def test_paginates_full_bodies_and_keeps_late_qualifications(self):
        with patch.object(jibe, 'get_json', side_effect=[
            dict(totalCount=2, jobs=[posting()]), dict(totalCount=2, jobs=[posting('2')])
        ]) as get, patch.object(jibe.time, 'sleep'):
            result = jibe.fetch(self.cfg)
        self.assertEqual(result.status, 'ok')
        self.assertEqual([j['source_id'] for j in result], ['1', '2'])
        self.assertGreater(len(result[0]['description']), 6000)
        self.assertIn('Qualifications: 0-1 years', result[0]['description'])
        self.assertEqual([c.kwargs['params']['page'] for c in get.call_args_list], [1, 2])
        self.assertTrue(all(c.kwargs['params']['country'] == 'India' for c in get.call_args_list))

    def test_brand_scope_and_correct_detail_url(self):
        cfg = dict(company='epsilon', host='careers.publicisgroupe.com', brand='Epsilon', job_path='/epsilon/jobs/')
        with patch.object(jibe, 'get_json', return_value=dict(totalCount=1, jobs=[posting()])) as get:
            result = jibe.fetch(cfg)
        self.assertEqual(get.call_args.kwargs['params']['tags2'], 'Epsilon')
        self.assertEqual(result[0]['url'], 'https://careers.publicisgroupe.com/epsilon/jobs/1')

    def test_foreign_wrong_employer_and_brand_rejected(self):
        for field, value in [('country', 'United States'), ('country', 'Indiana'),
                             ('client_code', 'other'), ('slug', '../other')]:
            row = posting(); row['data'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                jibe._job(row, self.cfg)
        row = posting(); row['data']['tags2'] = ['Other Publicis brand']
        with self.assertRaises(ValueError):
            jibe._job(row, dict(company='epsilon', host='example.test', brand='Epsilon'))

    def test_repeated_page_and_failed_later_page_preserve_partial(self):
        for second in [dict(totalCount=2, jobs=[posting()]), None]:
            with self.subTest(second=second), patch.object(jibe, 'get_json', side_effect=[
                dict(totalCount=2, jobs=[posting()]), second
            ]), patch.object(jibe.time, 'sleep'):
                result = jibe.fetch(self.cfg)
            self.assertEqual(result.status, 'partial')
            self.assertEqual(len(result), 1)

    def test_empty_missing_description_deadline_and_first_failure(self):
        with patch.object(jibe, 'get_json', return_value=dict(totalCount=0, jobs=[])):
            self.assertEqual(jibe.fetch(self.cfg).status, 'ok')
        row = posting(); row['data'].update(description='', qualifications='')
        with patch.object(jibe, 'get_json', return_value=dict(totalCount=1, jobs=[row])):
            self.assertEqual(jibe.fetch(self.cfg).status, 'partial')
        with patch.object(jibe, 'get_json', return_value=None), self.assertRaises(RuntimeError):
            jibe.fetch(self.cfg)
        with patch.object(jibe, 'get_json') as get, self.assertRaises(RuntimeError):
            jibe.fetch(self.cfg, time.monotonic() - 1)
        get.assert_not_called()
