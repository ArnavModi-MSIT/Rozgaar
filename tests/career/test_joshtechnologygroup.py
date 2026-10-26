import unittest
from unittest.mock import patch

from backend.fetchers import joshtechnologygroup as jtg

URL = jtg.SEARCH_URL+'engineer/'
LIST = '<div class="career-list__openings"><h2>Technical</h2><a class="career-list__opening" href="/careers/engineer/"><p>Engineer</p><span>Apply</span></a></div>'


def detail(body='<p>Required Experience: 0-1 years</p><p>Work Location: Gurgaon</p><p>Qualifications: Python</p>',canonical=URL):
    return f'<html><head><link rel="canonical" href="{canonical}"></head><body class="postid-123"><main><section class="career-list"><div class="career-list__title">Engineer</div><div class="career-list__content"></div><div class="career-list__openings">{body}<a class="btn" id="apply-now-clone">Apply Now</a><form>PRIVATE FORM FIELDS</form></div></section></main><footer>Company boilerplate</footer></body></html>'


class JoshTests(unittest.TestCase):
    def test_lists_all_sections_and_deduplicates_apply_links(self):
        html=LIST.replace('</div>','<h2>Other</h2><a href="/careers/sales/"><p>Sales</p></a><a href="/careers/engineer/">Apply</a></div>')
        jobs,_,errors=jtg._list(html)
        self.assertEqual(set(jobs),{URL,jtg.SEARCH_URL+'sales/'})
        self.assertEqual(jobs[URL],'Engineer')
        self.assertEqual(errors,[])

    def test_full_body_unicode_tail_and_form_exclusion(self):
        body='<p>Work Location: Gurugram – Work from office</p><p>'+'Intro '*1400+'</p><p>Required Experience: 2–4 years</p>'
        job=jtg._detail(detail(body),URL)
        self.assertGreater(len(job['description']),6000)
        self.assertIn('Required Experience: 2–4 years',job['description'])
        self.assertIn('India',job['location'])
        for text in ['Apply Now','PRIVATE FORM FIELDS','Company boilerplate']:
            self.assertNotIn(text,job['description'])

    def test_separate_location_label_and_unknown_are_not_hq_guesses(self):
        job=jtg._detail(detail('<p><strong>Work Location:</strong></p><p>• Gurgaon (WFO)</p><p>Qualifications: Python</p>'),URL)
        self.assertEqual(job['location'],'Gurgaon (WFO), India')
        job=jtg._detail(detail('<p>Qualifications: Python</p>'),URL)
        self.assertEqual(job['location'],'Unknown')

    def test_canonical_identity_and_untrusted_links_are_rejected(self):
        with self.assertRaises(ValueError):jtg._detail(detail(canonical=jtg.SEARCH_URL+'other/'),URL)
        for url in ['http://www.joshtechnologygroup.com/careers/engineer/','https://other.example/careers/engineer/','https://u:p@www.joshtechnologygroup.com/careers/engineer/']:
            with self.subTest(url=url),self.assertRaises(ValueError):jtg._url(url)

    def test_failed_detail_keeps_listing_and_stable_identity(self):
        with patch.object(jtg,'get_text',side_effect=[LIST,None]):failed=jtg.collect()
        with patch.object(jtg,'get_text',side_effect=[LIST,detail()]):success=jtg.collect()
        self.assertEqual(failed.status,'partial')
        self.assertEqual(failed[0]['description'],'')
        self.assertEqual(failed[0]['source_id'],success[0]['source_id'])
        self.assertEqual(success.status,'ok')

    def test_bad_layout_fails_but_verified_empty_is_success(self):
        with patch.object(jtg,'get_text',return_value='<html>Access denied</html>'),self.assertRaises(RuntimeError):jtg.collect()
        with patch.object(jtg,'get_text',return_value='<div class="career-list__openings"></div>'):
            self.assertEqual(jtg.collect().status,'ok')

    def test_repeated_pagination_retains_partial_results(self):
        html=LIST+'<div class="pagination"><a rel="next" href="/careers/">Next</a></div>'
        with patch.object(jtg,'get_text',side_effect=[html,detail()]):result=jtg.collect()
        self.assertEqual(result.status,'partial')
        self.assertEqual(len(result),1)
        self.assertIn('repeated listing',result.error)

    def test_deadline_and_registration(self):
        with patch.object(jtg,'get_text') as fetch,self.assertRaises(RuntimeError):jtg.collect(deadline=0)
        fetch.assert_not_called()
        from backend.core.collector import PLATFORMS
        import backend.config as config
        self.assertIn('joshtechnologygroup',dict(PLATFORMS))
        self.assertEqual(config.DISPLAY_NAMES['joshtechnologygroup'],'Josh Technology Group')
