import unittest
from unittest.mock import patch
from backend.fetchers import unitedhealthgroup as source

class UnitedHealthTests(unittest.TestCase):
    def test_country_normalization(self):
        self.assertEqual(source.india_location("Hyderabad, Telangana"),"Hyderabad, Telangana, India")
        self.assertIsNone(source.india_location("Eden Prairie, Minnesota"))
        self.assertIsNone(source.india_location("Delhi, United States"))
    def test_title_does_not_include_location(self):
        html='<section id="search-results" data-keywords="india" data-current-page="1" data-total-results="1" data-total-pages="1"><div id="search-results-list"><a data-job-id="123" href="/job/123"><h2>Engineer</h2><span class="job-location">Hyderabad, Telangana</span></a></div></section>'
        jobs,total,pages=source._parse_page(html,1)
        self.assertEqual(jobs[0]["title"],"Engineer")
        self.assertEqual(jobs[0]["location"],"Hyderabad, Telangana")
    def test_prefers_structured_description(self):
        html='<div class="ats-description">Short boilerplate</div><script type="application/ld+json">{"@type":"JobPosting","description":"<p>Python and SQL requirements</p>"}</script>'
        with patch.object(source,"_get",return_value=html):description=source._description({"url":"https://example.com"},None)
        self.assertEqual(description,"Python and SQL requirements")
