import unittest
from unittest.mock import patch
from fetchers import blackrock, paypal, standard, expedia

class MoreCareerSourcesTests(unittest.TestCase):
    def test_blackrock_country_facet_and_description(self):
        html = '<div id="search-results" data-current-page="1" data-total-results="1" data-total-pages="1"></div><div id="search-results-list"><a data-job-id="123" href="/job/123"><h2>Engineer</h2><span class="job-location"><span>Location:</span><span class="section3__job-info">Mumbai, Maharashtra</span></span></a></div>'
        with patch.object(blackrock, '_get', side_effect=[html, '<div class="ats-description">Python required</div>']):
            jobs = blackrock.collect()
        self.assertEqual(jobs.status, 'ok')
        self.assertEqual(jobs[0]['location'], 'Mumbai, Maharashtra, India')
        self.assertEqual(jobs[0]['description'], 'Python required')

    def test_paypal_india_facet_and_requisition_id(self):
        data = {'facets': [{'values': [{'facetParameter': 'locations', 'values': [{'id': 'in', 'descriptor': 'Chennai, India'}, {'id': 'us', 'descriptor': 'Indiana, USA'}]}]}]}
        self.assertEqual(paypal._india_location_ids(data), ['in'])
        job = paypal._job({'externalPath': '/job/Chennai/Engineer_R0138332', 'bulletFields': ['R0138332'], 'locationsText': '2 Locations'})
        self.assertEqual(job['source_id'], 'R0138332')
        self.assertEqual(job['location'], '2 Locations, India')

    def test_lever_confirmed_india_labels_only(self):
        for slug, location in [('cred', 'bengaluru'), ('meesho', 'Delhi NCR')]:
            self.assertEqual(standard._lever_location(slug, {'categories': {'location': location}}), location + ', India')
        self.assertEqual(standard._lever_location('cred', {'categories': {'location': 'London'}}), 'London')

    def test_expedia_blocked_request_is_failure(self):
        with patch.object(expedia, '_get', return_value=None):
            with self.assertRaises(RuntimeError): expedia.collect()

    def test_expedia_interrupted_pagination_is_partial(self):
        html = '<li class="Results__list__item"><a class="view-job-button" href="/jobs/R-1/"></a><h3 class="Results__list__title">Engineer</h3><h4 class="Results__list__location">India</h4><p>Technology</p></li>'
        with patch.object(expedia, '_get', side_effect=[html, None]), patch.object(expedia.time, 'sleep'):
            jobs = expedia.collect()
        self.assertEqual(jobs.status, 'partial')
        self.assertEqual(len(jobs), 1)
