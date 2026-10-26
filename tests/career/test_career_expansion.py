import unittest
from unittest.mock import patch

import backend.config as config
from backend.config.career_expansion import SOURCES
from backend.fetchers import standard


class CareerExpansionTests(unittest.TestCase):
    def test_new_sources_are_unique_registered_and_named(self):
        self.assertEqual(len(SOURCES), 50)
        self.assertEqual(len({row['key'].casefold() for row in SOURCES}), 50)
        for row in SOURCES:
            with self.subTest(company=row['key']):
                group = getattr(config, row['group'].upper())
                keys = [item if isinstance(item, str) else item.get('company') or item.get('company_id') for item in group]
                self.assertEqual(keys.count(row['key']), 1)
                self.assertEqual(config.DISPLAY_NAMES[row['key']], row['name'])
                self.assertTrue(row['career_url'].startswith('https://'))

    def test_india_scope_excludes_indiana_unknown_and_generic_remote(self):
        for location in ['Indianapolis, IN', 'Indiana', 'Remote', 'EMEA', 'Bangalore, United States', 'Puneville']:
            with self.subTest(location=location):
                self.assertEqual(standard._expansion_location(location), '')
        self.assertEqual(standard._expansion_location('Bangalore'), 'Bangalore, India')
        self.assertEqual(standard._expansion_location('Remote', country='IN'), 'Remote, India')
        self.assertEqual(standard._expansion_location('Bangalore', country='US'), '')

    def test_secondary_india_location_is_kept_without_claiming_us_primary(self):
        self.assertEqual(standard._expansion_location('New York, NY', ['Bengaluru, India'], 'US'), 'Bengaluru, India')

    def test_greenhouse_keeps_full_description_and_office_scope(self):
        rows = [dict(id=1,title='Engineer',location={'name':'Hybrid'},offices=[{'location':'Bengaluru, India'}],absolute_url='https://example.com/1',content='<p>'+'Intro '*1300+'</p><p>Qualifications: 0-1 years</p>'),
                dict(id=2,title='Engineer',location={'name':'Indiana'},absolute_url='https://example.com/2',content='Foreign')]
        with patch.object(standard, '_get', return_value={'jobs':rows}):
            jobs=standard.fetch_greenhouse('fivetran')
        self.assertEqual(len(jobs),1)
        self.assertIn('Qualifications: 0-1 years',jobs[0]['description'])
        self.assertGreater(len(jobs[0]['description']),6000)

    def test_samsara_explicit_office_code_and_no_arbitrary_prefix(self):
        self.assertEqual(standard._greenhouse_location('samsara',{'location':{'name':'Bengaluru - BLR1'}}),'Bengaluru, India')
        self.assertEqual(standard._greenhouse_location('samsara',{'location':{'name':'Bengaluru - US'}}),'')

    def test_lever_country_and_additional_locations(self):
        def posting(sid, country, location, extra=()):
            return dict(id=sid,text='Engineer',country=country,categories={'location':location,'allLocations':list(extra)},hostedUrl='https://example.com/'+sid,descriptionPlain='Introduction',lists=[{'text':'Qualifications','content':'<p>Python and SQL</p>'}],additionalPlain='Benefits')
        with patch.object(standard,'_get',return_value=[posting('1','US','Boston',['Bengaluru, India']),posting('2','IN','Remote'),posting('3','US','Indiana')]):
            jobs=standard.fetch_lever('acceldata')
        self.assertEqual([j['source_id'] for j in jobs],['1','2'])
        self.assertEqual(jobs[0]['location'],'Bengaluru, India')
        self.assertIn('Python and SQL',jobs[0]['description'])
        self.assertIn('Benefits',jobs[0]['description'])

    def test_ashby_structured_country_keeps_city_and_full_text(self):
        rows=[dict(id='1',title='Engineer',location='Bangalore HQ',address={'postalAddress':{'addressCountry':'IN'}},jobUrl='https://example.com/1',descriptionPlain='Full qualifications'),
              dict(id='2',title='Engineer',location='Remote',jobUrl='https://example.com/2',descriptionPlain='Foreign')]
        with patch.object(standard,'_get',return_value={'jobs':rows}):
            jobs=standard.fetch_ashby('tekion')
        self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['location'],'Bangalore HQ, India')
        self.assertEqual(jobs[0]['description'],'Full qualifications')
