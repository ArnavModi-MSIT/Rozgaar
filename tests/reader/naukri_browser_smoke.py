"""Naukri adapter fixtures; all requests intercepted, no website access."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
import url_reader.sources.naukri as naukri
import url_reader.engine as reader

JOB1 = "https://www.naukri.com/job-listings-analyst-intern-fixture-delhi-0-to-1-years-211026001234"
JOB2 = JOB1.replace("001234", "001235")
DETAIL = '''<h1>Analyst Intern</h1><div class="jd-header-comp-name"><a>Fixture Company</a></div>
<div class="job-desc">Build SQL dashboards.</div><div class="location">Delhi</div><div class="experience">0 years</div>
<div class="salary">Not disclosed</div><div class="key-skill"><a>SQL</a><a>Python</a></div>'''
STRUCTURED = {"@context": "https://schema.org", "@type": "JobPosting", "title": "Analyst Intern",
              "identifier": {"value": "211026001234"}, "hiringOrganization": {"name": "Fixture Company"},
              "description": "<p>Full responsibilities: build SQL dashboards and Python pipelines.</p><p>Qualifications: analytical skills.</p>",
              "datePosted": "2026-10-21", "employmentType": "INTERN"}
ENGINEER_SEARCH = "https://www.naukri.com/data-engineer-jobs-in-india?k=data%20engineer&l=india&qproductJobSource=2&naukriCampus=true&experience=0&jobAge=3&ctcFilter=75to100&ctcFilter=50to75&ctcFilter=25to50&ctcFilter=15to25&ctcFilter=10to15&ctcFilter=6to10"


def search_fixture(path):
    # Like the live site, the Next handler retains the query through client routing.
    # Direct document loads of page 2 are intercepted separately and drop filters.
    return f'''<div id="results"><a href="{JOB1}">First</a></div>
<a id="next" rel="next" href="{path}-2" onclick="event.preventDefault();
    const target=new window.URL(this.href); target.search=location.search;
    setTimeout(()=>{{history.pushState(null,'',target);
    document.getElementById('results').innerHTML='<a href={JOB2}>Second</a>';
    this.hidden=true; document.getElementById('last').hidden=false;}},150)">Next</a>
<button id="last" aria-label="Next" hidden disabled>Next</button>'''


def main():
    chrome = Path(os.environ.get("ProgramFiles", "/nonexistent"))/"Google/Chrome/Application/chrome.exe"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome) if chrome.exists() else None, headless=True)
        try:
            context = browser.new_context(service_workers="block")
            def route(request):
                url = request.request.url
                parts = urlsplit(url)
                if parts.path == "/blocked-jobs":
                    request.fulfill(status=403, content_type="text/html", body="<title>Access Denied</title>")
                    return
                if parts.path == urlsplit(JOB1).path:
                    body = DETAIL + '<script type="application/ld+json">' + json.dumps(STRUCTURED) + '</script>'
                elif parts.path.endswith("-2"):
                    # Keep the reset local; HTTP redirects can escape route interception.
                    body = '<script>history.replaceState(null,"",' + json.dumps(parts.path[:-2]) + ')</script>' + search_fixture(parts.path[:-2])
                    request.fulfill(content_type="text/html", body=body)
                    return
                elif parts.path.startswith("/analyst-jobs-in-delhi-ncr"):
                    assert parse_qs(parts.query)["ctcFilter"] == ["6to10", "10to15"]
                    body = search_fixture(parts.path)
                else:
                    body = search_fixture(parts.path)
                request.fulfill(status=200, content_type="text/html", body=body)
            context.route("**/*", route)
            page = context.new_page()
            reader.navigate(page, naukri.DEFAULT_SEARCH)
            assert reader.job_links(page) == [JOB1]
            assert reader.next_results(page).status == "advanced"
            assert reader.job_links(page) == [JOB2]
            assert reader.next_results(page).status == "verified_last_page"
            # Reproduce the reported redirect, then verify actual Next clicks retain
            # all six salary filters on the same data-engineer search.
            direct = naukri.filtered_next_url(ENGINEER_SEARCH, "https://www.naukri.com/data-engineer-jobs-in-india-2")
            page.goto(direct)
            assert not urlsplit(page.url).query
            reader.navigate(page, ENGINEER_SEARCH)
            assert reader.next_results(page).status == "advanced"
            assert reader.search_signature(page.url) == reader.search_signature(ENGINEER_SEARCH)
            assert parse_qs(urlsplit(page.url).query)["ctcFilter"] == ["75to100", "50to75", "25to50", "15to25", "10to15", "6to10"]
            assert reader.job_links(page) == [JOB2]
            assert reader.next_results(page).status == "verified_last_page"
            reader.navigate(page, "https://www.naukri.com/analyst-jobs-in-delhi-ncr?k=analyst&experience=0&ctcFilter=6to10&ctcFilter=10to15")
            assert reader.next_results(page).status == "advanced"
            assert reader.job_links(page) == [JOB2]
            assert reader.next_results(page).status == "verified_last_page"
            # A checkpoint on numbered page 2 must reopen the original search,
            # skip its saved job, and reach the next job through the real control.
            resumed = {"search_url": ENGINEER_SEARCH, "jobs": [{"link": JOB1}], "errors": [],
                       "progress": {"results_page_url": direct, "pending_links": [],
                                    "attempted_links": [JOB1], "page_complete": True}}
            calls = []
            def read_fixture(url):
                calls.append(url)
                return {"link": url, "title": "Second", "company": "Fixture", "description": "Available full duties."}
            with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
                reader.collect_jobs(page, SimpleNamespace(read=read_fixture), SimpleNamespace(limit=2, delay=0),
                                    resumed, Path(folder)/"resume.json")
            assert resumed["status"] == "completed" and calls == [JOB2], resumed
            assert reader.search_signature(page.url) == reader.search_signature(ENGINEER_SEARCH)
            record = reader.read_job(page, JOB1)
            assert record["source"] == "naukri" and record["job_id"] == "211026001234", record
            assert record["company"] == "Fixture Company" and record["skills"] == ["SQL", "Python"], record
            assert record["extraction_method"] == "jobposting_jsonld", record
            assert "Qualifications" in record["description"] and "<p>" not in record["description"], record
            assert record["date_posted"] == "2026-10-21"
            try:
                reader.navigate(page, "https://www.naukri.com/blocked-jobs")
            except reader.AccessBlocked:
                pass
            else:
                raise AssertionError("Denied access was not stopped")
            print("Naukri browser fixtures passed: client-side Next, page-2 redirect reproduction, six retained salary filters, JSON-LD details and denied-access stop.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
