"""Offline Instahyre UI fixtures; all browser requests are intercepted."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
import url_reader.sources.instahyre as instahyre
import url_reader.engine as reader

JOB1 = "https://www.instahyre.com/job-12345/"
JOB2 = "https://www.instahyre.com/job-12346/"
SLUG1 = "https://www.instahyre.com/job-12345-analyst-at-fixture-delhi/"
SEARCH_HTML = '''<div class="tab selected" id="tab">Recommended jobs 1</div>
<div id="counts">Showing 1 - 1 out of 1 jobs</div>
<button class="skills-search-btn" onclick="runSearch()">Search</button>
<div>Experience Level <div class="slider" style="width:200px;height:30px">
<div class="slider-track" style="width:200px;height:10px;background:gray" onclick="applyYears()"></div>
<span class="slider-value" id="years">All</span></div><div>0 years 25+</div></div>
<div id="cards"><a id="employer-profile-opportunity"><ul id="job-skills-99999"><li>Recommended only</li></ul></a></div>
<div class="pagination"><li id="next" hidden onclick="nextPage()">Next »</li></div>
<button onclick="window.forbidden=true">Apply</button><button onclick="window.forbidden=true">Not interested</button>
<script>
window.forbidden=false;
history.replaceState(null,'','/candidate/opportunities/?matching=true');
function card(id) {return '<a id="employer-profile-opportunity"><h2>Fixture Analyst</h2><ul id="job-skills-'+id+'"><li>SQL</li></ul></a>';}
function render(id) {
    const old=document.getElementById('cards'); old.className='ng-leave'; old.id='leaving';
    const fresh=document.createElement('div'); fresh.id='cards'; fresh.innerHTML=card(id);
    old.after(fresh); setTimeout(()=>old.remove(),600);
}
function runSearch() {
    history.replaceState(null,'','/candidate/opportunities/?company_size=0&job_type=0&search=true');
    document.getElementById('tab').innerText='Search Results 2';
    document.getElementById('counts').innerText='Showing 1 - 1 out of 2 jobs';
    render('12345'); document.getElementById('next').hidden=false;
}
function applyYears() {
    const url=new window.URL(location.href); url.searchParams.set('years','0'); history.replaceState(null,'',url);
    document.getElementById('years').innerText='0';
}
function nextPage() {
    setTimeout(()=>{render('12346'); document.getElementById('counts').innerText='Showing 2 - 2 out of 2 jobs';
    document.getElementById('next').hidden=true;},150);
}
</script>'''
DETAIL_HTML = '''<div class="profile-info"><h1>Data Analyst</h1><h2 class="company-name">at Fixture</h2>
<div class="job-locations"><span class="location-span">Delhi</span><span class="experience">0-1 Years</span></div></div>
<ul id="job-skills-description"><li>SQL</li><li>Python</li></ul>
<div class="profile-content job-description"><p>Responsibilities: build SQL reports.</p><p>Qualifications: Python and analytics.</p></div>
<div>Unrelated company promotion and recommended jobs.</div><button onclick="window.forbidden=true">Apply now</button>'''


def main():
    chrome = Path(os.environ.get("ProgramFiles", "/nonexistent"))/"Google/Chrome/Application/chrome.exe"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome) if chrome.exists() else None, headless=True)
        try:
            context = browser.new_context(service_workers="block")
            state = {"login": False, "blocked": False}
            def route(request):
                assert request.request.method == "GET", "A fixture attempted to submit a form"
                url = request.request.url
                if "/login/" in url:
                    request.fulfill(content_type="text/html", body="<title>Login - Instahyre</title><input type=password>")
                elif "/candidate/opportunities/" in url:
                    if state["blocked"]:
                        request.fulfill(status=403, content_type="text/html", body="<title>Access Denied</title>")
                    elif state["login"]:
                        request.fulfill(content_type="text/html", body="<script>location.replace('/login/')</script>")
                    else:
                        request.fulfill(content_type="text/html", body=SEARCH_HTML)
                elif url == JOB1:
                    request.fulfill(content_type="text/html", body=f"<script>location.replace({json.dumps(SLUG1)})</script>")
                else:
                    request.fulfill(content_type="text/html", body=DETAIL_HTML)
            context.route("**/*", route)
            page, detail = context.new_page(), context.new_page()
            reader.navigate(page, instahyre.DEFAULT_SEARCH)
            assert instahyre.search_active(page)
            assert "years=0" in page.url
            assert instahyre.job_links(page) == [JOB1]
            assert not page.locator(".ng-leave").count()
            record = reader.read_job(detail, JOB1)
            assert record["link"] == SLUG1 and record["company"] == "Fixture", record
            assert record["experience"] == "0-1 Years" and record["skills"] == ["SQL", "Python"], record
            assert "Qualifications" in record["description"] and "Unrelated" not in record["description"]
            origin = page.url
            assert reader.next_results(page).status == "advanced"
            assert page.url == origin and instahyre.job_links(page) == [JOB2]
            assert reader.next_results(page).status == "verified_last_page"
            # Replaying a run skips its previously saved ID, even with an unchanged URL.
            result = {"search_url": reader.search_url(instahyre.DEFAULT_SEARCH), "jobs": [record], "errors": [],
                      "progress": {"results_page_url": origin, "pending_links": [], "attempted_links": [JOB1], "page_complete": True}}
            with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
                reader.collect_jobs(page, SimpleNamespace(read=lambda url: reader.read_job(detail, url)),
                                    SimpleNamespace(limit=2, delay=0), result, Path(folder)/"resume.json")
                saved = json.loads((Path(folder)/"resume.json").read_text(encoding="utf-8"))
            assert result["status"] == "completed" and len(saved["jobs"]) == 2, result
            assert not page.evaluate("window.forbidden") and not detail.evaluate("window.forbidden || false")
            # A different selected category must produce no links.
            page.locator("#tab").evaluate("el=>el.innerText='Applied jobs 1'")
            assert reader.job_links(page) == []
            for mode in ("login", "blocked"):
                state[mode] = True
                try:
                    reader.navigate(page, instahyre.DEFAULT_SEARCH)
                except reader.AccessBlocked:
                    pass
                else:
                    raise AssertionError(f"{mode} did not stop the reader")
                state[mode] = False
            print("Instahyre browser fixtures passed: Search Results, zero years, leaving-card exclusion, stable-ID redirects, details, same-URL pagination, resume, no Apply and access stops.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
