"""Offline rendered Wellfound fixtures: every browser request is intercepted."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
import url_reader.engine as reader
import url_reader.sources.wellfound as wellfound

SEARCH = "https://wellfound.com/location/india?remote=true"
JOB1 = "https://wellfound.com/jobs/12345-analyst"
JOB2 = "https://wellfound.com/jobs/12346-engineer"
DESCRIPTION = "Responsibilities: build SQL reports and Python pipelines. " * 200


def main():
    chrome = Path(os.environ.get("ProgramFiles", "/nonexistent"))/"Google/Chrome/Application/chrome.exe"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome) if chrome.exists() else None, headless=True)
        try:
            context = browser.new_context(service_workers="block")
            state = {"login": False, "blocked": False, "missing": False, "delay_next": True, "signed": False}
            def route(request):
                assert request.request.method == "GET", "Reader attempted a submission"
                url = request.request.url
                parts = urlsplit(url)
                if parts.path == "/login":
                    body = "<title>Login - Wellfound</title><input type=password>"
                elif parts.path.startswith("/jobs/"):
                    if parts.path == "/jobs/12345":
                        request.fulfill(content_type="text/html", body="<script>location.replace(" + json.dumps(JOB1) + ")</script>")
                        return
                    identifier = "12346" if "12346" in url else "12345"
                    posting = {"@type": "JobPosting", "identifier": {"value": identifier},
                               "title": "Data Analyst", "hiringOrganization": {"name": "Fixture"},
                               "description": "<p>" + DESCRIPTION + "</p><p>Final requirement: graduation 2027.</p>",
                               "employmentType": "INTERN", "datePosted": "2026-10-22",
                               "jobLocation": {"address": {"addressLocality": "Delhi", "addressCountry": "India"}},
                               "baseSalary": {"currency": "INR", "value": {"value": 25000, "unitText": "MONTH"}}}
                    body = '<main><h1>Data Analyst</h1><ul><li>Delhi · Internship</li></ul><a href="/company/fixture">Fixture</a>'
                    if not state["missing"]:
                        body += '<div id="job-description">Short preview</div><script type="application/ld+json">' + json.dumps({"@graph": [posting]}) + '</script>'
                    body += '<aside>Unrelated recommendation</aside><button onclick="window.forbidden=true">Apply</button></main>'
                    if state["signed"]:
                        body = '<h1>Data Analyst at Fixture</h1><span>Posted yesterday</span><a href="/company/fixture"><img alt="Fixture"></a><a href="/company/fixture">Fixture</a><div id="description-slot"></div>'
                        if not state["missing"]:
                            description = '<div class="styles_description__36q7q"><p>' + DESCRIPTION + '</p><h3>Requirements</h3><p>Final signed-in requirement: graduation 2027.</p></div>'
                            body += '<script>setTimeout(()=>document.getElementById("description-slot").innerHTML=' + json.dumps(description) + ',1500)</script>'
                        body += '<h3>Similar jobs to Data Analyst at Fixture</h3><div class="styles_description__414vs">' + ('Unrelated recommendation ' * 1800) + '</div><h3>About Fixture</h3><div class="styles_description__other">Company marketing</div>'
                elif state["blocked"]:
                    request.fulfill(status=403, content_type="text/html", body="<title>Access denied</title>")
                    return
                elif state["login"]:
                    request.fulfill(content_type="text/html", body="<script>location.replace('/login')</script>")
                    return
                elif parts.path == "/jobs":
                    body = '<main><h1>Trending startup jobs</h1><a href="' + JOB1 + '">Analyst</a><a href="/location/united-states">View all jobs</a></main>'
                else:
                    second = "page=2" in parts.query
                    job = JOB2 if second else JOB1
                    body = '<main><h1>Jobs in India</h1><h4>Page ' + ("2" if second else "1") + ' of 2</h4><a href="' + job + '">Job</a><a href="' + job + '?ref=duplicate">Alias</a><a href="/jobs/not-numeric">Search</a><a hidden href="/jobs/99999-hidden">Hidden</a>'
                    if not second:
                        body += '<a aria-label="Next page" href="/location/india?remote=true&amp;page=2">Next</a>'
                    body += '<button onclick="window.forbidden=true">Save</button></main><footer><a href="/jobs/88888-footer">Other</a></footer>'
                    if second and state["delay_next"]:
                        body = '<h1>Jobs in India</h1><h4>Page 2 of 2</h4><div id="cards"></div><script>setTimeout(()=>{document.getElementById("cards").innerHTML=' + json.dumps('<a href="' + JOB2 + '">Delayed engineer</a>') + '},6000)</script>'
                request.fulfill(content_type="text/html", body=body.replace("<main>", "<div>").replace("</main>", "</div>"))
            context.route("**/*", route)
            page, detail = context.new_page(), context.new_page()
            reader.navigate(page, SEARCH)
            assert reader.collect_links(page, 20) == [JOB1]
            record = reader.read_job(detail, "https://wellfound.com/jobs/12345")
            assert record["link"] == JOB1 and record["company"] == "Fixture", record
            assert record["location"] == "Delhi, India" and record["salary"] == "INR 25000 MONTH", record
            assert record["date_posted"] == "2026-10-22" and record["employment_type"] == "INTERN"
            assert DESCRIPTION.strip() in record["description"] and record["description"].endswith("graduation 2027."), record["description"][-100:]
            assert "Unrelated" not in record["description"] and record["description_length"] > 10000
            assert reader.next_results(page).status == "advanced"
            state["delay_next"] = False
            assert reader.search_signature(page.url) == reader.search_signature(SEARCH)
            assert reader.job_links(page) == [JOB2]
            assert reader.next_results(page).status == "verified_last_page"
            result = {"search_url": SEARCH, "jobs": [record], "errors": [], "progress": {
                "results_page_url": SEARCH, "pending_links": [], "attempted_links": [JOB1], "page_complete": True}}
            with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
                output = Path(folder)/"resume.json"
                reader.collect_jobs(page, SimpleNamespace(read=lambda url: reader.read_job(detail, url)),
                                    SimpleNamespace(limit=2, delay=0), result, output)
                saved = json.loads(output.read_text(encoding="utf-8"))
                assert result["status"] == "completed" and len(saved["jobs"]) == 2, saved
                assert {job["job_id"] for job in saved["jobs"]} == {"12345", "12346"}
            assert not page.evaluate("window.forbidden || false") and not detail.evaluate("window.forbidden || false")
            reader.navigate(page, wellfound.DEFAULT_SEARCH)
            outcome = reader.next_results(page)
            assert not outcome and outcome.status == "curated_list_end" and outcome.method == "curated_jobs_page" and page.url == wellfound.DEFAULT_SEARCH
            assert not outcome.error and "highlights list" in outcome.reason
            # The real collection path records the explanatory outcome without following US View all.
            landing_result = {"search_url": wellfound.DEFAULT_SEARCH, "jobs": [record], "errors": [], "progress": {
                "results_page_url": wellfound.DEFAULT_SEARCH, "pending_links": [], "attempted_links": [JOB1], "page_complete": True}}
            with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
                reader.collect_jobs(page, SimpleNamespace(read=lambda url: reader.read_job(detail, url)),
                                    SimpleNamespace(limit=200, delay=0), landing_result, Path(folder)/"landing.json")
            assert landing_result["status"] == "partial" and "highlights list" in landing_result["stop_reason"]
            assert landing_result["pagination"]["status"] == "curated_list_end" and page.url == wellfound.DEFAULT_SEARCH
            state["signed"] = True
            signed = reader.read_job(detail, JOB1)
            assert signed["title"] == "Data Analyst" and signed["company"] == "Fixture", signed
            assert signed["extraction_method"] == "signed_in_dom" and signed["description"].endswith("graduation 2027.")
            assert DESCRIPTION.strip() in signed["description"] and "Unrelated recommendation" not in signed["description"]
            assert "Company marketing" not in signed["description"]
            state["missing"] = True
            try:
                reader.read_job(detail, JOB1)
            except ValueError as exc:
                assert "description was missing" in str(exc)
            else:
                raise AssertionError("Empty posting was saved")
            for mode in ("login", "blocked"):
                state[mode] = True
                try:
                    reader.navigate(page, SEARCH)
                except reader.AccessBlocked:
                    pass
                else:
                    raise AssertionError(mode + " did not stop collection")
                state[mode] = False
            print("Wellfound browser fixtures passed: visible ID deduplication, full description, metadata, slug redirect, filter-preserving Next, checkpoint resume, curated landing scope, missing-description rejection, no Apply/Save, login/403 stops.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
