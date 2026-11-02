import unittest
from unittest.mock import patch

from backend.fetchers import avature

HOST = "recruitment.example.com"
CFG = {"company": "acme", "host": HOST, "path": "/en_US/careers", "query": "1=%5B2%5D"}


def article(job_id, title, office):
    return (f'<article class="article article--result"><div class="article__header"><h3>'
            f'<a class="link" href="https://{HOST}/en_US/careers/JobDetail?jobId={job_id}">{title}</a></h3></div>'
            f'<div class="article__details__data"><p class="icon">ID</p><p>{job_id}</p></div>'
            f'<div class="article__details__data"><img alt="Office Location:"><p>{office}</p></div></article>')


def results(total, *articles):
    return f"<html><body><p>{total} results</p>{''.join(articles)}</body></html>"


def detail(title, body="Build dashboards in SQL and Python."):
    return (f'<main><h2 class="title title--11">{title}</h2>'
            '<div class="article__content__view__field field--location"><p>Gurugram</p></div>'
            '<div class="article__content__view__field field--date"><p>02-Nov-2026</p></div>'
            f'<div class="article__content__view__field"><p>{body}</p></div>'
            '<div class="article__content__view__field"><p>Apply by Friday.</p></div></main>')


class ParseTests(unittest.TestCase):
    def test_results_keep_indian_offices_and_report_total(self):
        html = results(77, article("1", "Analyst", "Gurugram Office"), article("2", "Quant", "Sydney Office"),
                       article("3", "DE", "Hyderabad Office"))
        jobs, total, rows = avature.parse_results(html, HOST)
        self.assertEqual((total, rows), (77, 3))
        self.assertEqual([(j["source_id"], j["location"]) for j in jobs],
                         [("1", "Gurugram, India"), ("3", "Hyderabad, India")])

    def test_foreign_link_host_is_rejected(self):
        bad = results(1, article("1", "A", "Gurugram Office").replace(HOST, "evil.example.org"))
        with self.assertRaises(ValueError):
            avature.parse_results(bad, HOST)

    def test_detail_drops_metadata_fields(self):
        title, text = avature.parse_detail(detail("Analyst"))
        self.assertEqual(title, "Analyst")
        self.assertEqual(text, "Build dashboards in SQL and Python.\n\nApply by Friday.")
        self.assertNotIn("02-Nov", text)


class FetchTests(unittest.TestCase):
    def run_fetch(self, pages, details):
        def fake_get(_session, url, **_kw):
            if "SearchJobs" in url:
                return pages.pop(0)
            return details[url.rsplit("=", 1)[1]]
        with patch.object(avature, "get_text", fake_get), patch.object(avature.time, "sleep"):
            return avature.fetch(CFG)

    def test_offset_follows_server_page_size_and_reads_descriptions(self):
        pages = [results(3, article("1", "A", "Gurugram Office"), article("2", "B", "Hyderabad Office")),
                 results(3, article("3", "C", "Mumbai Office"))]
        result = self.run_fetch(pages, {"1": detail("A"), "2": detail("B"), "3": detail("C")})
        self.assertEqual(result.status, "ok")
        self.assertEqual([j["source_id"] for j in result], ["1", "2", "3"])
        self.assertEqual(result[0]["company"], "acme")
        self.assertTrue(result[2]["description"].startswith("Build dashboards"))

    def test_detail_for_a_different_job_is_not_attached(self):
        pages = [results(1, article("1", "A", "Gurugram Office"))]
        result = self.run_fetch(pages, {"1": detail("Some Other Role")})
        self.assertEqual(result.status, "partial")
        self.assertEqual(result[0]["description"], "")
        self.assertIn("description unavailable: 1", result.error)

    def test_repeated_page_stops_with_partial(self):
        same = results(50, article("1", "A", "Gurugram Office"))
        result = self.run_fetch([same, same], {"1": detail("A")})
        self.assertEqual(result.status, "partial")
        self.assertIn("repeated listing page", result.error)

    def test_unavailable_first_page_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([None], {})

    def test_only_foreign_rows_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([results(1, article("1", "A", "Sydney Office"))], {})


if __name__ == "__main__":
    unittest.main()
