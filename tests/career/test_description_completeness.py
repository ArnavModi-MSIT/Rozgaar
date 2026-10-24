import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.core.description_quality import description_quality
from backend.fetchers import oracle, icims, standard, successfactors


class CompleteDescriptionTests(unittest.TestCase):
    def test_oracle_retains_qualifications_after_six_thousand_characters(self):
        data = {'items':[{'ExternalDescriptionStr':'<p>'+'Background ' * 900+'</p>',
                          'ExternalQualificationsStr':'<p>Requires 4 years of Python experience.</p>'}]}
        with patch.object(oracle, '_get', return_value=data):
            text = oracle.fetch_requisition_detail('https://example.test', '1')
        self.assertGreater(len(text), 6000)
        self.assertTrue(text.endswith('Requires 4 years of Python experience.'))

    def test_icims_retains_qualification_tail(self):
        data = {'totalCount':1,'jobs':[{'data':{'req_id':'1','title':'Analyst','country':'India',
                 'description':'<p>'+'Background ' * 900+'</p><p>Requires 5 years of SQL experience.</p>'}}]}
        with patch.object(icims, '_fetch_page', return_value=data):
            text = icims.fetch_icims({'company':'example','jobs_domain':'example.test'})[0]['description']
        self.assertGreater(len(text), 6000)
        self.assertTrue(text.endswith('Requires 5 years of SQL experience.'))

    def test_shared_html_helper_preserves_full_text_by_default(self):
        text = 'Background ' * 900 + 'Final qualification.'
        self.assertEqual(standard.strip_html('<p>'+text+'</p>'), text)
        self.assertEqual(len(standard.strip_html(text, max_chars=100)), 100)

    def test_known_cap_is_suspicious_even_with_trailing_whitespace(self):
        self.assertEqual(description_quality('x'*5999+' '), 'possibly_truncated')
        self.assertEqual(description_quality('x'*6001), 'available')

    def test_rmk_uses_supported_locale_and_fetches_schema_description(self):
        rec = {'id':'63918','unifiedStandardTitle':'Business Analyst','urlTitle':'Insights-&amp;-Analytics',
               'supportedLocales':['en_GB'],'jobLocationShort':['Chennai, IND'],'jobLocationCountry':['India']}
        response = SimpleNamespace(raise_for_status=lambda:None, json=lambda:{'jobSearchResult':[{'response':rec}]})
        html = '<span itemprop="description"><p>Actual responsibilities and qualifications.</p></span>'
        with patch.object(successfactors.SESSION, 'post', return_value=response), patch.object(successfactors, 'get_text', return_value=html) as get:
            jobs = successfactors.fetch_successfactors_rmk({'company':'example','host':'example.test','category_id':1,'fetch_details':True})
        self.assertEqual(jobs[0]['url'], 'https://example.test/job/Insights-&-Analytics/63918-en_GB')
        self.assertEqual(jobs[0]['description'], 'Actual responsibilities and qualifications.')
        self.assertEqual(get.call_args.args[1], jobs[0]['url'])


if __name__ == '__main__':
    unittest.main()
