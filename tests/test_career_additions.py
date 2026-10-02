import unittest
from unittest.mock import patch
from fetchers import intuit, standard, workday

class CareerAdditionsTests(unittest.TestCase):
    def test_intuit_country_pages_and_description(self):
        def page(n, job):
            return f'<div id="search-results" data-current-page="{n}" data-total-results="2" data-total-pages="2"></div><div id="search-results-list"><a data-job-id="{job}" href="/job/{job}"><h2>Engineer</h2><span class="job-location">Bangalore, India</span></a></div>'
        with patch.object(intuit, '_get', side_effect=lambda url: page(2, 'b') if url.endswith('/2/2') else (page(1, 'a') if url == intuit.SEARCH_URL else '<section class="job-description">Python required</section>')):
            jobs = intuit.collect()
        self.assertEqual(jobs.status, 'ok')
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]['title'], 'Engineer')
        self.assertEqual(jobs[0]['location'], 'Bangalore, India')
        self.assertEqual(jobs[0]['description'], 'Python required')

    def test_intuit_deadline_is_partial(self):
        html = '<div id="search-results" data-current-page="1" data-total-results="2" data-total-pages="2"></div>'
        with patch.object(intuit, '_get', return_value=html):
            self.assertEqual(intuit.collect(deadline=0).status, 'partial')

    def test_arcesium_india_cities_without_foreign_contamination(self):
        self.assertEqual(standard._greenhouse_location('arcesiumllc', {'location': {'name': 'Bengaluru; Hyderabad'}}), 'Bengaluru; Hyderabad, India')
        self.assertEqual(standard._greenhouse_location('arcesiumllc', {'location': {'name': 'New York'}}), 'New York')

    def test_walmart_country_prefix(self):
        cfg = {'company': 'walmart', 'tenant': 'walmart', 'wd_server': 'wd504', 'site': 'WalmartExternal'}
        data = {'total': 1, 'jobPostings': [{'title': 'Engineer', 'locationsText': 'IN KA BANGALORE', 'externalPath': '/job/1'}]}
        with patch.object(workday, '_post', return_value=data):
            self.assertEqual(workday.fetch_workday(cfg)[0]['location'], 'IN KA BANGALORE, India')

    def test_walmart_us_multilocation_is_not_unknown(self):
        cfg = {'company': 'walmart', 'tenant': 'walmart', 'wd_server': 'wd504', 'site': 'WalmartExternal'}
        data = {'total': 1, 'jobPostings': [{'title': '(USA) Engineer', 'locationsText': '2 Locations', 'externalPath': '/job/1'}]}
        with patch.object(workday, '_post', return_value=data):
            self.assertEqual(workday.fetch_workday(cfg)[0]['location'], '2 Locations, United States')
