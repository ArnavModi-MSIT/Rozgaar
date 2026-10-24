import json
import unittest
from unittest.mock import patch
from backend.fetchers import career_html as c
from backend.fetchers import tredence


class CareerHTMLTests(unittest.TestCase):
    def test_lowes_reads_full_embedded_description_instead_of_intro(self):
        full = '<p>Company background</p>' * 1000 + '<h2>Required Qualifications</h2><p>5 years of experience</p>'
        data = {'jobDetail':{'status':200,'data':{'job':{'jobId':'JR-1','description':full}}}}
        html = '<script>phApp.ddo = '+json.dumps(data)+'; phApp.pageId = 1;</script><script type="application/ld+json">'+json.dumps({'@type':'JobPosting','description':'Brief introduction'})+'</script>'
        desc = c.lowes_description(html,'JR-1')
        self.assertIn('5 years of experience',desc)
        self.assertGreater(len(desc),10000)

    def test_lowes_rejects_description_for_different_job(self):
        data = {'jobDetail':{'status':200,'data':{'job':{'jobId':'JR-other','description':'Wrong posting'}}}}
        self.assertEqual(c.lowes_description('<script>phApp.ddo = '+json.dumps(data)+'</script>','JR-1'),'')

    def test_lowes_empty_json_ld_uses_verified_page_data(self):
        data = {'jobDetail':{'status':200,'data':{'job':{'jobId':'JR-1','description':'<p>SQL requirements</p>'}}}}
        html = '<script type="application/ld+json"></script><script>phApp.ddo = '+json.dumps(data)+'</script>'
        self.assertEqual(c.lowes_description(html,'JR-1'),'SQL requirements')

    def test_nested_structured_description_keeps_late_requirements(self):
        desc = '<p>Background</p>' * 1000 + '<h2>Requirements</h2><p>5+ years of experience</p>'
        html = '<script type="application/ld+json">' + json.dumps({'@graph':[{'@type':'JobPosting','description':desc}]}) + '</script>'
        self.assertIn('5+ years of experience', c.job_description(html))
        self.assertNotIn('<p>', c.job_description(html))

    def test_nutanix_repeated_page_is_partial(self):
        html = '''Displaying 1 to 20 of 21 matching jobs
        <div class="card-job" data-id="1"><a class="js-view-job" href="/en/jobs/1/test/">Engineer</a><p class="job-meta-location">Delhi, India</p></div>'''
        with patch.object(c, 'get_text', return_value=html), patch.object(c, 'job_description', return_value='Requirements: SQL'), patch.object(c.time, 'sleep'):
            jobs = c.fetch('nutanix')
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.status, 'partial')

    def test_nutanix_india_filter_survives_pagination(self):
        def page(sid):
            return f'''Displaying 1 to 1 of 2 matching jobs <div class="card-job" data-id="{sid}"><a class="js-view-job" href="/en/jobs/{sid}/test/">Engineer</a><p class="job-meta-location">Delhi, India</p></div>'''
        with patch.object(c, 'get_text', side_effect=[page('1'),page('2'), 'detail', 'detail']) as get, patch.object(c,'job_description',return_value='Required Qualifications: SQL'), patch.object(c.time,'sleep'):
            jobs = c.fetch('nutanix')
        self.assertEqual(len(jobs),2)
        self.assertEqual(jobs.status,'ok')
        for index in (0,1):
            url = get.call_args_list[index].args[1]
            self.assertIn('country=India',url)
            self.assertIn('pagesize=20',url)
            self.assertIn(f'page={index+1}',url)

    def test_nutanix_ignored_country_filter_is_failure(self):
        html = '''Displaying 1 to 1 of 1 matching jobs <div class="card-job" data-id="1"><a class="js-view-job" href="/en/jobs/1/test/">Engineer</a><p class="job-meta-location">Tokyo, Japan</p></div>'''
        with patch.object(c,'get_text',return_value=html):
            with self.assertRaisesRegex(RuntimeError,'India filter'):
                c.fetch('nutanix')

    def test_blocked_html_is_not_successful_zero(self):
        with patch.object(c, 'get_text', return_value=None):
            with self.assertRaises(RuntimeError): c.fetch('mathworks')

    def test_mathworks_country_prefix_and_total(self):
        html = '''<a id="max_link_bottom">1</a><td class="search_result_desc"><div class="search_title"><a href="/company/jobs/opportunities/123-engineer">Engineer</a></div><div class="additional_field"><span>IN-Hyderabad</span></div></td>'''
        rows,total = c.parse_listing(html, 'mathworks', 'https://www.mathworks.com')
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]['location'], 'India, Hyderabad')

    def test_maq_atom_excludes_us_and_retains_full_text(self):
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Engineer</title><id>tag:jobscore.com,2026:/abc</id><category scheme="http://schemas.jobscore.com/atom#location" term="Noida, India"/><link rel="alternate" href="https://careers.jobscore.com/abc"/><content type="html">&lt;p&gt;Requirements: 3 years experience&lt;/p&gt;</content></entry><entry><title>US Engineer</title><category scheme="http://schemas.jobscore.com/atom#location" term="Plano, TX"/></entry></feed>'''
        jobs = c.parse_maq_feed(xml)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['source_id'], 'abc')
        self.assertIn('3 years', jobs[0]['description'])

    def test_micron_failed_first_page_is_not_zero(self):
        with patch.object(c, 'get_json', return_value=None):
            with self.assertRaises(RuntimeError): c.collect_micron()

    def test_sap_flight_payload_reads_country_filtered_count(self):
        payload = '1:["$",null,{"jobs":[{"id":"1","locations":"Bangalore, India"}],"totalJobs":1}]'
        html = '<script>self.__next_f.push('+json.dumps([1,payload])+')</script>'
        jobs,total = c.sap_listing(html)
        self.assertEqual(total, 1)
        self.assertEqual(jobs[0]['id'], '1')

    def test_mathworks_feed_uses_location_country_not_description(self):
        xml = '''<rss><channel><item><id>1</id><title_raw>Engineer</title_raw><link>https://www.mathworks.com/job/1</link><location><city>Noida</city><country>IN</country></location><summary>SQL work</summary><required_qualifications>4 years experience</required_qualifications></item><item><id>2</id><location><country>US</country></location><summary>Works with India</summary></item></channel></rss>'''
        jobs = c.parse_mathworks_feed(xml)
        self.assertEqual(len(jobs), 1)
        self.assertIn('Required Qualifications\n4 years experience', jobs[0]['description'])

    def test_tredence_known_offices_do_not_admit_global_remote(self):
        self.assertEqual(tredence.india_location('Bangalore'), 'Bangalore, India')
        self.assertEqual(tredence.india_location('San Jose (TR)'), '')
        self.assertEqual(tredence.india_location('Remote'), '')

    def test_tredence_search_preserves_required_public_parameters(self):
        response = {'totalJobCount':1,'jobVoList':[{'jobSeq':'1','jobTitle':'Engineer','locations':'Bangalore'}]}
        with patch.object(tredence,'post_json',return_value=response) as post, patch.object(tredence,'get_json',return_value={'jobVO':{'jobSeq':'1','jobDesc':'<p>5 years experience</p>'}}):
            jobs = tredence.collect()
        params = json.loads(post.call_args.kwargs['data']['careerSiteUrlParams'])
        self.assertEqual(params['search'], '*:*')
        self.assertEqual(params['page'], 0)
        self.assertEqual(jobs.status,'ok')
        self.assertIn('5 years', jobs[0]['description'])

if __name__ == '__main__': unittest.main()
