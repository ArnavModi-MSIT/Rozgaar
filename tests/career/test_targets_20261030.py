import json
import unittest
from unittest.mock import patch

import backend.config as config
from backend.config.career_targets_20261030 import SOURCES, INDIA_BOARDS
from backend.fetchers import employer_portals, standard
from scripts.career.company_inventory import inventory
from rojgaar.paths import ROOT


class TargetExpansionTests(unittest.TestCase):
    def test_all_100_targets_have_an_honest_outcome(self):
        audit = json.loads((ROOT / 'docs/catalog/CAREER_TARGETS_20261030.json').read_text(encoding='utf-8'))
        rows = audit['targets']
        self.assertEqual(sorted(r['number'] for r in rows), list(range(1, 101)))
        self.assertEqual(sum(r['status'] == 'unresolved' for r in rows), 72)
        self.assertEqual(sum(r['status'] == 'already_connected' for r in rows), 1)
        connected = [r for r in rows if r['status'].startswith('connected')]
        self.assertEqual({r['key'] for r in connected}, {r['key'] for r in SOURCES})
        self.assertEqual(sum(r['status'] == 'connected_empty' for r in connected), 2)
        self.assertTrue(all(r['notes'] for r in rows if r['status'] == 'unresolved'))
        self.assertEqual([r['number'] for r in rows if r['status'] == 'already_connected'], [18])

    def test_registered_once_named_and_adapters_available(self):
        self.assertEqual(len(SOURCES), 27)
        self.assertEqual(len({r['target'] for r in SOURCES}), 27)
        self.assertNotIn('c5i', {r['key'] for r in SOURCES})
        for row in SOURCES:
            with self.subTest(key=row['key']):
                group = getattr(config, row['group'].upper())
                keys = [v if isinstance(v, str) else v.get('company') or v.get('company_id') for v in group]
                self.assertEqual(keys.count(row['key']), 1)
                self.assertEqual(config.DISPLAY_NAMES[row['key']], row['name'])
                if row['group'] == 'employer_portals':
                    self.assertIn(row['config']['kind'], employer_portals.ADAPTERS)
                self.assertNotIn('salary', row)
        self.assertIn('Nielsen', inventory())
        self.assertIn('NielsenIQ', inventory())

    def test_new_standard_boards_use_positive_india_scope(self):
        self.assertTrue(INDIA_BOARDS.issubset(standard.INDIA_BOARDS))
        for row in SOURCES:
            key, group = row['key'], row['group']
            if group not in {'greenhouse', 'lever', 'ashby'}:
                continue
            if group == 'greenhouse':
                payload = {'jobs': [dict(id=1, title='Engineer', location={'name':'Remote'}, absolute_url='https://example.test/1'),
                                    dict(id=2, title='Engineer', location={'name':'Bengaluru, India'}, absolute_url='https://example.test/2')]}
            elif group == 'lever':
                payload = [dict(id='1', text='Engineer', categories={'location':'Remote'}, hostedUrl='https://example.test/1'),
                           dict(id='2', text='Engineer', country='IN', categories={'location':'Remote'}, hostedUrl='https://example.test/2')]
            else:
                payload = {'jobs': [dict(id='1', title='Engineer', location='Remote', jobUrl='https://example.test/1'),
                                    dict(id='2', title='Engineer', location='India', jobUrl='https://example.test/2')]}
            with self.subTest(key=key), patch.object(standard, '_get', return_value=payload):
                result = getattr(standard, 'fetch_' + group)(key)
            self.assertEqual([j['source_id'] for j in result], ['2'])
