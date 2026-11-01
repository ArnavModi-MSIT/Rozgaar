import unittest
from unittest.mock import patch
from backend.fetchers import dataweave

class DataWeaveTests(unittest.TestCase):
    def test_full_detail_and_location(self):
        listing='<h2>Current Openings</h2><a href="/jobs/group/job1">Apply</a>'
        detail='<div id="printthis" class="jobcontent"><h1>Architect</h1><h2>Skills &amp; Requirements</h2><p>'+('Python ' * 1100)+'</p><p>Last qualification</p><p>Job Location: Bangalore, India</p><form>Private application form</form></div>'
        with patch.object(dataweave, 'get_text', side_effect=[listing,detail]):
            jobs=dataweave.fetch({})
        self.assertEqual(jobs.status,'ok')
        self.assertEqual(len(jobs),1)
        self.assertGreater(len(jobs[0]['description']),6000)
        self.assertIn('Last qualification',jobs[0]['description'])
        self.assertNotIn('Private application form',jobs[0]['description'])
    def test_failed_search_is_not_empty_success(self):
        with patch.object(dataweave, 'get_text', return_value=None), self.assertRaises(RuntimeError):
            dataweave.fetch({})
