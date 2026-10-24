import unittest
from unittest.mock import patch
from backend.fetchers import standard, jibe, mediatek, millennium, juspay, tesco, target

class FifteenSourcesTests(unittest.TestCase):
    def test_new_greenhouse_boards_exclude_foreign_city_only_jobs(self):
        jobs = [{'id':1,'title':'Engineer','absolute_url':'https://example.com/1','location':{'name':'Bengaluru; Gurugram'},'content':'Python'}, {'id':2,'title':'Engineer','absolute_url':'https://example.com/2','location':{'name':'Taipei'},'content':'Python'}]
        with patch.object(standard, '_get', return_value={'jobs':jobs}):
            result = standard.fetch_greenhouse('mongodb')
        self.assertEqual([job['source_id'] for job in result], ['1'])
        self.assertEqual(result[0]['location'], 'Bengaluru; Gurugram, India')

    def test_jibe_country_metadata_overrides_site_building_label(self):
        data = {'totalCount':1,'jobs':[{'data':{'req_id':'42','title':'Engineer','location_name':'Bangalore BH','city':'Bangalore','state':'Karnataka','country':'India','description':'Python'}}]}
        with patch.object(jibe.icims, '_fetch_page', return_value=data):
            jobs = jibe.collect('booking','jobs.booking.com','/booking/jobs')
        self.assertEqual(jobs.status,'ok')
        self.assertEqual(jobs[0]['location'],'Bangalore, Karnataka, India')
        self.assertEqual(jobs[0]['url'],'https://jobs.booking.com/booking/jobs/42')

    def test_jibe_truncated_result_is_partial(self):
        data = {'totalCount':2,'jobs':[{'data':{'req_id':'42','title':'Engineer','country':'India','description':'Python'}}]}
        with patch.object(jibe.icims, '_fetch_page', side_effect=[data,None]):
            self.assertEqual(jibe.collect('amd','careers.amd.com','/jobs').status,'partial')

    def test_mediatek_location_uses_city_code_not_numeric_label(self):
        row = {'id':'MT1','title':'Engineer','description':'Python','properties':{'location':{'label':'0000168800','code':'Bangalore\t'}}}
        self.assertEqual(mediatek._job(row)['location'],'Bangalore, India')
        row['properties']['location']['code'] = 'West Lafayette, IN'
        self.assertIsNone(mediatek._job(row))

    def test_mediatek_global_total_controls_pagination_not_india_count(self):
        row = {'id':'MT1','title':'Engineer','description':'Python','properties':{'location':{'code':'Noida'}}}
        data = {'result':{'data':{'json':{'jobs':[row], 'pagination':{'current_page':1,'total_pages':1,'total_items':1}}}}}
        with patch.object(mediatek,'get_json',return_value=data):
            jobs = mediatek.collect()
        self.assertEqual(jobs.status,'ok')
        self.assertEqual(len(jobs),1)

    def test_millennium_public_schema_and_truncation(self):
        data = {'count':2,'positions':[{'id':1,'name':'Engineer','locations':['Bangalore, India'],'department':'Technology'}]}
        with patch.object(millennium,'get_json',side_effect=[data,None]):
            jobs = millennium.collect()
        self.assertEqual(jobs.status,'partial')
        self.assertEqual(jobs[0]['description'],'Department: Technology')

    def test_juspay_explicit_empty_is_success(self):
        with patch.object(juspay,'get_text',return_value='<main>No global job openings available at the moment</main>'):
            self.assertEqual(juspay.collect().status,'ok')
        with patch.object(juspay,'get_text',return_value='<html>Forbidden</html>'):
            with self.assertRaises(RuntimeError): juspay.collect()

    def test_tesco_search_normalization(self):
        html = '<div class="article__header__text"><h3 class="article__header__text__title"><a href="https://careers.tesco.com/en_GB/careers/JobDetail/Engineer/42">Engineer</a></h3><span class="list-item-location">Bengaluru, India</span></div><p>1-1 of 1 results</p>'
        jobs,total = tesco._page(html)
        self.assertEqual(total,1)
        self.assertEqual(jobs[0]['source_id'],'42')

    def test_target_pagination_country_site(self):
        html = '<div id="search-results" data-current-page="1" data-total-results="1" data-total-pages="1"></div><div id="search-results-list"><a data-job-id="42" href="/job/bengaluru/engineer/42"><h2>Engineer</h2></a></div>'
        with patch.object(target,'_get',side_effect=[html,'<div class="ats-description">Python</div>']):
            jobs=target.collect()
        self.assertEqual(jobs.status,'ok')
        self.assertEqual(jobs[0]['location'],'India')
