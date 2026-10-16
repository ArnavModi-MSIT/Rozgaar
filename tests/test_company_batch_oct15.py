import json
import unittest
from unittest.mock import patch

from fetchers import employer_portals as portals, standard, workable, workday_india


class EmployerPortalTests(unittest.TestCase):
    def test_keka_keeps_india_and_qualification_at_end(self):
        rows = [dict(id=1, title="Analyst", description="<p>" + "Intro " * 2000 + "</p><p>Qualifications: 3+ years of experience</p>",
                     experience="3 - 5 Years", jobLocations=[dict(countryCode="IN", city="Mumbai")]),
                dict(id=2, title="Analyst", description="US", jobLocations=[dict(countryCode="US", city="Boston")])]
        with patch.object(portals, "get_json", return_value=rows):
            result = portals.fetch_keka(dict(company="wingify", host="wingify.keka.com"))
        self.assertEqual(len(result), 1)
        self.assertIn("3+ years", result[0]["description"])
        self.assertIn("India", result[0]["location"])
        self.assertTrue(result[0]["url"].endswith("/jobdetails/1"))

    def test_keka_empty_and_unavailable_are_different(self):
        cfg = dict(company="wingify", host="wingify.keka.com")
        with patch.object(portals, "get_json", return_value=[]):
            self.assertEqual(portals.fetch_keka(cfg).status, "ok")
        with patch.object(portals, "get_json", return_value=None):
            with self.assertRaises(RuntimeError):
                portals.fetch_keka(cfg)

    def test_darwinbox_counts_all_countries_before_filtering(self):
        foreign = dict(id="1", title="Analyst", country="United States", jd="Foreign")
        india = dict(id="2", title="Analyst", country="India", locations="Mumbai, India", jd="<p>0 years experience</p>", experience="0 - 2 Years")
        responses = [dict(status="success", job_counts=2, data=[foreign]), dict(status="success", job_counts=2, data=[india])]
        with patch.object(portals, "post_json", side_effect=responses):
            result = portals.fetch_darwinbox(dict(company="porter", host="porter.darwinbox.in"))
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["2"])
        self.assertIn("Experience: 0 - 2 Years", result[0]["description"])

    def test_darwinbox_repeated_page_reports_partial(self):
        row = dict(id="1", title="Analyst", country="India", jd="Full JD")
        with patch.object(portals, "post_json", return_value=dict(status="success", job_counts=2, data=[row])):
            result = portals.fetch_darwinbox(dict(company="porter", host="porter.darwinbox.in"))
        self.assertEqual(result.status, "partial")
        self.assertIn("received 1 of 2", result.error)

    def test_darwinbox_failed_first_page_is_not_empty_success(self):
        with patch.object(portals, "post_json", return_value=None):
            with self.assertRaises(RuntimeError):
                portals.fetch_darwinbox(dict(company="porter", host="porter.darwinbox.in"))

    def test_kula_adjacent_utf8_text_records_resolve_by_byte_length(self):
        first, second = "<p>Rôle — data\nIndia</p>", "<p>Requirements: 1+ years</p>"
        stream = ':HL["style"]\n1:{}\n2:T' + format(len(first.encode()), "x") + "," + first
        stream += "3:T" + format(len(second.encode()), "x") + "," + second
        self.assertEqual(portals._kula_description("$2", stream), first)
        self.assertEqual(portals._kula_description("$3", stream), second)
        self.assertEqual(portals._kula_description("$9", stream), "")

    def test_kula_uses_country_metadata_and_excludes_confidential_jobs(self):
        rows = [dict(id=i, title="Analyst", listed=True, is_confidential=(i == 3),
                     ats_job=dict(job_description="Full qualifications", offices=[dict(country_code=country, city="Mumbai" if country == "IN" else "Boston")]))
                for i, country in [(1, "IN"), (2, "US"), (3, "IN")]]
        stream = '1:' + json.dumps(dict(jobs=rows, accountName="clevertap"), separators=(",", ":")) + "\n"
        html = "<script>self.__next_f.push(" + json.dumps([1, stream]) + ")</script>"
        with patch.object(portals, "get_text", return_value=html):
            result = portals.fetch_kula(dict(company="clevertap", account="clevertap"))
        self.assertEqual([j["source_id"] for j in result], ["1"])
        self.assertEqual(result.status, "ok")

    def test_kula_wrong_account_rejected(self):
        html = '<script>self.__next_f.push([1,"1:{}\\n"])</script>'
        with patch.object(portals, "get_text", return_value=html):
            with self.assertRaises(RuntimeError):
                portals.fetch_kula(dict(company="clevertap", account="clevertap"))

    def test_trakstar_incomplete_pagination_is_partial(self):
        html = '<p>View 2 Openings</p><a href="/jobs/fk1/"><h3 class="js-job-list-opening-name">Analyst</h3><div class="js-job-list-opening-loc" title="Bengaluru"></div></a>'
        detail = '<div class="js-job-title">Analyst</div><div class="jobdesciption"><p>Qualifications: 0-2 years</p></div>'
        with patch.object(portals, "get_text", side_effect=[html, html, detail]):
            result = portals.fetch_trakstar(dict(company="whatfix", host="whatfix101.hire.trakstar.com"))
        self.assertEqual(result.status, "partial")
        self.assertIn("received 1 of 2", result.error)
        self.assertIn("0-2 years", result[0]["description"])

    def test_trakstar_redirect_to_different_job_is_not_accepted(self):
        html = '<p>View 1 Openings</p><a href="/jobs/fk1/"><h3 class="js-job-list-opening-name">Analyst</h3><div class="js-job-list-opening-loc" title="India"></div></a>'
        detail = '<div class="js-job-title">Different job</div><div class="jobdesciption">Wrong JD</div>'
        with patch.object(portals, "get_text", side_effect=[html, detail]):
            result = portals.fetch_trakstar(dict(company="whatfix", host="whatfix101.hire.trakstar.com"))
        self.assertEqual(result[0]["description"], "")
        self.assertEqual(result.status, "partial")

    def test_oracle_paginates_global_list_but_enriches_only_india(self):
        first = dict(items=[dict(TotalJobsCount=2, requisitionList=[dict(Id="US1", Title="US", PrimaryLocationCountry="US", PrimaryLocation="Boston")])])
        second = dict(items=[dict(TotalJobsCount=2, requisitionList=[dict(Id="IN1", Title="Analyst", PrimaryLocationCountry="IN", PrimaryLocation="Pune, India")])])
        detail = dict(items=[dict(ExternalDescriptionStr="<p>" + "Intro " * 2000 + "</p>", ExternalQualificationsStr="<p>Minimum 4 years of experience</p>")])
        with patch.object(portals, "get_json", side_effect=[first, second, detail]) as get:
            result = portals.fetch_oracle_india(dict(company="bny", base_url="https://example.com", site="Careers"))
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result), 1)
        self.assertIn("4 years", result[0]["description"])
        self.assertEqual(get.call_count, 3)

    def test_oracle_failure_not_empty_success(self):
        with patch.object(portals, "get_json", return_value=None):
            with self.assertRaises(RuntimeError):
                portals.fetch_oracle_india(dict(company="bny", base_url="https://example.com", site="Careers"))

    def test_successfactors_country_code_and_full_qualifications(self):
        html = '<p>Results 1 – 1 of 1</p><tr class="data-row"><td><a class="jobTitle-link" href="/job/Engineer/123/">Engineer</a><span class="jobLocation">Bengaluru, IN</span></td></tr>'
        detail = '<div data-careersite-propertyid="description">' + 'Intro ' * 2000 + '<p>Qualifications: 1+ years of experience</p></div>'
        with patch.object(portals, "get_text", side_effect=[html, detail]):
            result = portals.fetch_successfactors(dict(company="anz", host="careers.anz.com"))
        self.assertEqual(result.status, "ok")
        self.assertEqual(result[0]["location"], "Bengaluru, India")
        self.assertIn("1+ years", result[0]["description"])

    def test_pcsx_reads_full_job_instead_of_department_stub(self):
        rows = [dict(id=i, name="Engineer", standardizedLocations=[loc]) for i, loc in
                [(1, "Bengaluru, KA, IN"), (2, "Indianapolis, IN, US")]]
        description = "Requirements: 3+ years of experience"
        html = '<script type="application/ld+json">' + json.dumps(dict(__unused=True, **{"@type": "JobPosting", "title": "Engineer", "description": description})) + '</script>'
        with patch.object(portals, "get_json", return_value=dict(data=dict(count=2, positions=rows))), patch.object(portals, "get_text", return_value=html):
            result = portals.fetch_pcsx(dict(company="eightfoldai", host="app.eightfold.ai", domain="volkscience.com"))
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["1"])
        self.assertEqual(result[0]["description"], description)

    def test_successfactors_india_pin_does_not_treat_indiana_zip_as_india(self):
        cards = ''.join('<tr class="data-row"><td><a class="jobTitle-link" href="/job/Engineer/'+str(i)+'/">Engineer</a><span class="jobLocation">'+loc+'</span></td></tr>' for i, loc in [(1, 'Bangalore, KA, IN, 560066'), (2, 'Indianapolis, IN, 46204')])
        html = '<p>Results 1 – 2 of 2</p>' + cards
        detail = '<div data-careersite-propertyid="description">Full JD</div>'
        with patch.object(portals, "get_text", side_effect=[html, detail]):
            result = portals.fetch_successfactors(dict(company="exxonmobil", host="jobs.exxonmobil.com"))
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["1"])


class ExistingAdapterExpansionTests(unittest.TestCase):
    def test_cloudflare_in_office_never_means_india(self):
        foreign = dict(id=1, title="Engineer", absolute_url="https://example.com/1", location=dict(name="In-Office"),
                       content="Full JD", metadata=[dict(name="Job Posting Location", value=["Austin, US"])])
        india = dict(foreign, id=2, metadata=[dict(name="Job Posting Location", value=["Bengaluru, India"])])
        with patch.object(standard, "_get", return_value=dict(jobs=[foreign, india])):
            result = standard.fetch_greenhouse("cloudflare")
        self.assertEqual([j["source_id"] for j in result], ["2"])
        self.assertEqual(result[0]["location"], "Bengaluru, India")

    def test_observeai_city_label_uses_full_office_country(self):
        row = dict(id=1, title="Engineer", absolute_url="https://example.com", content="JD", location=dict(name="Bengaluru"),
                   offices=[dict(location="Bengaluru, Karnataka, India")])
        with patch.object(standard, "_get", return_value=dict(jobs=[row])):
            self.assertEqual(standard.fetch_greenhouse("observeai")[0]["location"], "Bengaluru, Karnataka, India")

    def test_uipath_uses_structured_country_not_city_guess(self):
        rows = [dict(id=str(i), title="Engineer", location="Bangalore", jobUrl="https://example.com", descriptionPlain="JD",
                     address=dict(postalAddress=dict(addressCountry=country))) for i, country in [(1, "India"), (2, "United States")]]
        with patch.object(standard, "_get", return_value=dict(jobs=rows)):
            self.assertEqual([j["source_id"] for j in standard.fetch_ashby("uipath")], ["1"])

    def test_workable_current_flat_schema_deduplicates_and_filters_country(self):
        india = dict(title="Analyst", shortcode="123", country="India", city="Chennai", description="Full JD")
        foreign = dict(india, shortcode="US", country="United States", city="Boston")
        with patch.object(workable, "_get", return_value=dict(jobs=[india, india, foreign])):
            result = workable.fetch_workable("tiger-analytics")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["location"], "Chennai, India")

    def test_workday_explicit_facet_pattern_does_not_match_indiana(self):
        data = dict(facets=[dict(facetParameter="locations", values=[dict(id="in", descriptor="Bangalore, In"), dict(id="us", descriptor="Indianapolis, IN")])])
        self.assertEqual(workday_india._facets(data, r"^Bangalore,\s*IN$"), {"locations": ["in"]})

    def test_workday_checks_detail_country_for_new_scoped_feeds(self):
        first = dict(jobPostings=[], facets=[dict(facetParameter="locationCountry", values=[dict(id="in", descriptor="India")])])
        rows = [dict(title="Engineer", externalPath="/job/" + str(i), bulletFields=[str(i)], locationsText="India") for i in [1, 2]]
        def detail(session, url, **kwargs):
            return dict(jobPostingInfo=dict(country=dict(descriptor="India" if url.endswith("1") else "United States"), location="Mumbai", jobDescription="Full JD"))
        cfg = dict(company="new", tenant="new", wd_server="wd1", site="Jobs", verify_detail_country=True)
        with patch.object(workday_india, "post_json", side_effect=[first, dict(total=2, jobPostings=rows)]), patch.object(workday_india, "get_json", side_effect=detail):
            result = workday_india.fetch(cfg)
        self.assertEqual([j["source_id"] for j in result], ["1"])
        self.assertEqual(result.status, "partial")

    def test_workday_multi_country_job_keeps_explicit_india_option_only(self):
        row = dict(title="Engineer", externalPath="/job/1", bulletFields=["1"], locationsText="Multiple Locations")
        info = dict(country=dict(descriptor="United States"), location="Boston", additionalLocations=["Pune, India", "London, UK"], jobDescription="Full JD")
        cfg = dict(company="new", tenant="new", wd_server="wd1", site="Jobs", verify_global_country=True)
        with patch.object(workday_india, "post_json", side_effect=[dict(jobPostings=[row]), dict(total=1, jobPostings=[row])]), patch.object(workday_india, "get_json", return_value=dict(jobPostingInfo=info)):
            result = workday_india.fetch(cfg)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result[0]["location"], "Pune, India")

    def test_workday_bad_detail_does_not_discard_other_valid_jobs(self):
        rows = [dict(title="Engineer", externalPath="/job/"+str(i), bulletFields=[str(i)]) for i in [1, 2]]
        def detail(session, url, **kwargs):
            return dict(jobPostingInfo=[]) if url.endswith("2") else dict(jobPostingInfo=dict(country=dict(descriptor="India"), location="Pune", jobDescription="Full JD"))
        cfg = dict(company="new", tenant="new", wd_server="wd1", site="Jobs", verify_global_country=True)
        with patch.object(workday_india, "post_json", side_effect=[dict(jobPostings=rows), dict(total=2, jobPostings=rows)]), patch.object(workday_india, "get_json", side_effect=detail):
            result = workday_india.fetch(cfg)
        self.assertEqual(result.status, "partial")
        self.assertEqual([j["source_id"] for j in result], ["1"])


if __name__ == "__main__":
    unittest.main()
