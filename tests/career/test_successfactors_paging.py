import unittest
from unittest.mock import patch

from backend.fetchers import successfactors

CFG = {"company": "acme", "host": "careers.example.com"}


def row(job_id):
    return (f'<tr class="data-row"><td><a class="jobTitle-link" href="/job/Pune-Role-{job_id}/{job_id}/">Role {job_id}</a>'
            f'<span class="jobLocation">Pune, Maharashtra, IN</span></td></tr>')


def page(ids, total=None):
    label = f'<span class="paginationLabel">Results 1 &ndash; {len(ids)} of {total}</span>' if total else ""
    return f"<html><body>{label}<table>{''.join(row(i) for i in ids)}</table></body></html>"


class PagingTests(unittest.TestCase):
    def run_fetch(self, pages):
        starts = []

        def fake(_host, startrow):
            starts.append(startrow)
            return pages.pop(0) if pages else ""
        with patch.object(successfactors, "_search_page", fake), patch.object(successfactors.time, "sleep"):
            return successfactors.fetch_successfactors(CFG), starts

    def test_small_pages_follow_the_site_total(self):
        # Vodafone Idea serves 7 rows per page; the old fixed 25-row rule stopped after page 1.
        jobs, starts = self.run_fetch([page(range(1, 8), 15), page(range(8, 15), 15), page([15], 15)])
        self.assertEqual(len(jobs), 15)
        self.assertEqual(starts, [0, 7, 14])

    def test_large_pages_do_not_refetch_overlap(self):
        # Nomura serves 100 rows per page.
        jobs, starts = self.run_fetch([page(range(1, 101), 150), page(range(101, 151), 150)])
        self.assertEqual(len(jobs), 150)
        self.assertEqual(starts, [0, 100])

    def test_without_a_total_a_short_page_still_ends_the_listing(self):
        jobs, starts = self.run_fetch([page(range(1, 26)), page(range(26, 30))])
        self.assertEqual(len(jobs), 29)
        self.assertEqual(starts, [0, 25])

    def test_repeated_rows_stop_pagination(self):
        jobs, starts = self.run_fetch([page(range(1, 8), 50), page(range(1, 8), 50)])
        self.assertEqual(len(jobs), 7)
        self.assertEqual(starts, [0, 7])


if __name__ == "__main__":
    unittest.main()


class ScopedTenantTests(unittest.TestCase):
    def test_path_query_and_country_scope_for_prefixed_tenants(self):
        urls = []

        def fake_get(_session, url, **_kw):
            urls.append(url)
            return ('<html><span class="paginationLabel">Results 1 &ndash; 1 of 1</span><table>'
                    '<tr class="data-row"><td><a class="jobTitle-link" href="/ey/job/Bengaluru-Role/77/">Role</a>'
                    '<span class="jobLocation">Bengaluru, KA, IN, 560016 +10 more&hellip;</span></td></tr></table></html>')
        cfg = {"company": "ey", "host": "careers.ey.com", "path": "/ey/search/",
               "extra_query": "locationsearch=India", "country_scoped": "India"}
        with patch.object(successfactors, "get_text", fake_get), patch.object(successfactors.time, "sleep"):
            jobs = successfactors.fetch_successfactors(cfg)
        self.assertEqual(urls[0], "https://careers.ey.com/ey/search/?q=&sortColumn=referencedate&sortDirection=desc&startrow=0&locationsearch=India")
        self.assertEqual(jobs[0]["location"], "Bengaluru, India")
        self.assertEqual(jobs[0]["url"], "https://careers.ey.com/ey/job/Bengaluru-Role/77/")

    def test_default_tenants_keep_the_root_search_path(self):
        urls = []

        def fake_get(_session, url, **_kw):
            urls.append(url)
            return "<html></html>"
        with patch.object(successfactors, "get_text", fake_get):
            successfactors.fetch_successfactors({"company": "x", "host": "h.example.com"})
        self.assertTrue(urls[0].startswith("https://h.example.com/search/?q="))


class RmkLocationTests(unittest.TestCase):
    def test_city_country_style_for_wipro_fields(self):
        record = {"jobLocationShort": ["Hyderabad, IND-36, IND, 500032<br/>"], "sfstd_jobLocation_obj": ["Hyderabad"],
                  "jobLocationCountry": ["India"]}
        self.assertEqual(successfactors._rmk_location(record, "city_country"), "Hyderabad, India")
        self.assertEqual(successfactors._rmk_location({"jobLocationCountry": ["India"]}, "city_country"), "India")

    def test_default_styles_are_unchanged(self):
        self.assertEqual(successfactors._rmk_location({"custprimecity": "Mumbai", "custCountryRegion": ["India"]}), "Mumbai, India")
        self.assertEqual(successfactors._rmk_location({"jobLocationShort": ["Pune, India "]}), "Pune, India")

    def test_rmk_fetch_sends_category_zero_and_facet_filter(self):
        bodies = []

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"jobSearchResult": [{"response": {"id": "9", "unifiedStandardTitle": "Analyst", "urlTitle": "Analyst",
                                                           "sfstd_jobLocation_obj": ["Pune"], "jobLocationCountry": ["India"],
                                                           "supportedLocales": ["en_US"]}}], "totalJobs": 1}

        def fake_post(url, json=None, headers=None, timeout=None):
            bodies.append(json)
            return Resp()
        cfg = {"company": "wipro", "host": "careers.wipro.com", "variant": "rmk", "category_id": 0,
               "facet_filters": {"jobLocationCountry": ["India"]}, "location_style": "city_country"}
        with patch.object(successfactors.SESSION, "post", fake_post), patch.object(successfactors.time, "sleep"):
            jobs = successfactors.fetch_successfactors_rmk(cfg)
        self.assertEqual(bodies[0]["categoryId"], 0)
        self.assertEqual(bodies[0]["facetFilters"], {"jobLocationCountry": ["India"]})
        self.assertEqual(jobs[0]["location"], "Pune, India")
        self.assertEqual(jobs[0]["url"], "https://careers.wipro.com/job/Analyst/9-en_US")
