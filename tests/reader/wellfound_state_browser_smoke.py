"""Rendered filter-state and borrowed-tab regression; all site requests intercepted."""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
import url_reader.engine as reader
import url_reader.supervisor as supervised_reader
import url_reader.browser.wellfound_session as wellfound_session
import url_reader.sources.wellfound as wellfound

SEARCH = "https://wellfound.com/jobs"
JOB1 = "https://wellfound.com/jobs/12345-fixture"
JOB2 = "https://wellfound.com/jobs/12346-fixture"
SEARCH_HTML = '''<style>h1{height:50px} #filters{height:220px;position:sticky;top:0;background:white;z-index:2} #count{height:40px} h1,#filters,#count,#cards{margin-left:180px}</style>
<aside style="position:fixed;left:0;top:120px;width:140px">Home | Profile | Jobs | Applied</aside>
<h1>Search for jobs</h1><section id="filters"><nav>Browse all | Saved <span id="saved-count">0</span> | Hidden</nav>
<input placeholder="Add a job title" value=""><input aria-label="Location" value="Delhi">
<button>Internship</button><button id="experience">0-1 years</button><button>Clear All</button><button>Filters</button></section>
<div id="count">289 results</div><div id="cards"><a href="/jobs/12345-fixture">First job</a></div>
<button aria-label="Next page" onclick="document.getElementById('cards').innerHTML='<a href=/jobs/12346-fixture>Second job</a>';document.getElementById('count').innerText='288 results';this.disabled=true">Next</button>
<button onclick="window.forbidden=true">Save</button><button onclick="window.forbidden=true">Apply</button><div style="height:1200px"></div>'''

# Matches the live Wellfound layout: collapsed search fields are buttons,
# and the remote preference is a combobox, with no native input elements.
BUTTON_SEARCH_HTML = SEARCH_HTML.replace(
    '<input placeholder="Add a job title" value=""><input aria-label="Location" value="Delhi">',
    '<button data-test="SearchBar-RoleSelect-FocusButton">Add a job title</button>'
    '<button id="location">India</button><div role="combobox" aria-labelledby="RemotePreference-label"><button>ASIA</button></div>')


def main():
    chrome = Path(os.environ.get("ProgramFiles", "/nonexistent"))/"Google/Chrome/Application/chrome.exe"
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder, sync_playwright() as p:
        folder = Path(folder)
        context = p.chromium.launch_persistent_context(str(folder/"chrome"), executable_path=str(chrome) if chrome.exists() else None,
            headless=True, service_workers="block", args=[f"--remote-debugging-port={port}", "--remote-debugging-address=127.0.0.1"])
        search = context.pages[0]
        search_requests = []
        layout = {'buttons': False}
        def route(request):
            assert request.request.method == "GET"
            url = request.request.url
            if url == SEARCH:
                search_requests.append(url)
                body = BUTTON_SEARCH_HTML if layout['buttons'] else SEARCH_HTML
            else:
                body = '<h1>Data Intern at Fixture</h1><a href="/company/fixture">Fixture</a><div class="styles_description__36q7q"><p>Full SQL and Python responsibilities. Eligible student requirements.</p></div><h3>Similar jobs to Data Intern at Fixture</h3><div class="styles_description__414vs">Unrelated company recommendation</div>'
            request.fulfill(content_type="text/html", body=body)
        context.route("**/*", route)
        try:
            layout['buttons'] = True
            search.goto(SEARCH)
            assert search.locator('input,select,textarea').count() == 0
            custom = wellfound_session.capture(search)
            assert any(item['value'] == 'India' for item in custom['inputs']), custom
            assert any(item['value'] == 'ASIA' for item in custom['inputs']), custom
            search.evaluate('window.scrollTo(0,700)')
            assert wellfound_session.capture(search)['fingerprint'] == custom['fingerprint']
            search.locator('#location').evaluate("el=>el.innerText='Delhi'")
            assert wellfound_session.capture(search)['fingerprint'] != custom['fingerprint'], 'Custom location change was not detected'
            search.locator('#filters button,#filters [role="combobox"]').evaluate_all('els=>els.forEach(el=>el.remove())')
            try:
                wellfound_session.capture(search)
            except reader.PlaywrightError as exc:
                assert 'No supported visible search inputs' in str(exc)
            else:
                raise AssertionError('Unrecognized empty filter controls were accepted')
            layout['buttons'] = False
            search_requests.clear()
            search.goto(SEARCH)
            state = wellfound_session.capture(search)
            assert all(text in state["header_text"] for text in ("Delhi", "Internship", "0-1 years")), state
            assert state["result_count"] == 289
            assert "Home" not in state["header_text"] and "Profile" not in state["header_text"]
            search.evaluate("window.scrollTo(0,700)")
            assert wellfound_session.capture(search)["fingerprint"] == state["fingerprint"], "Fixed sidebar entered the search fingerprint while scrolling"
            search.locator('#saved-count').evaluate("el=>el.innerText='6'")
            assert wellfound_session.capture(search)["fingerprint"] == state["fingerprint"], "Saved count changed the filter identity"
            # A company card contains multiple independent postings; title and
            # Learn more anchors for the same posting must only deduplicate by ID.
            rows = ''.join(f'<article><a href="/jobs/{sid}-title">Role {sid}</a><a href="/jobs/{sid}-learn-more">Learn more</a></article>' for sid in (12345, 12346, 12347))
            search.locator('#cards').evaluate('(el,html)=>el.innerHTML=html', '<section><h2>One company</h2>'+rows+'</section>')
            search._wellfound_search_state = state
            links = wellfound.collect_links(search, 1)
            assert len(links) == 3 and {reader.posting_key(link)[1] for link in links} == {'12345','12346','12347'}, links
            search.locator('#cards').evaluate("el=>el.innerHTML='<a href=/jobs/12345-fixture>First job</a>'")
            search.evaluate("window.scrollTo(0,0)")
            cdp = f"http://127.0.0.1:{port}"
            selection = wellfound_session.inspect(cdp)
            assert selection["state"]["fingerprint"] == state["fingerprint"]
            assert wellfound_session.find_page(context, selection["target"], state) is search
            args = SimpleNamespace(url=SEARCH, output=folder/"direct.json", fresh=False, limit=2, delay=0,
                                   search_state=state, wellfound_target=selection["target"], stop_event=threading.Event())
            value = {"jobs": [], "errors": []}
            reader.prepare_output(args, value, SEARCH)
            owned = []
            detail = reader.DetailReader(context, owned)
            reader.collect_jobs(search, detail, args, value, args.output)
            assert value["status"] == "completed" and len(value["jobs"]) == 2, value
            assert all(job["title"] == "Data Intern" and job["extraction_method"] == "signed_in_dom" for job in value["jobs"])
            assert value["pages_advanced"] == 1 and search.url == SEARCH
            assert len(search_requests) == 1, "Collector reopened the filtered search"
            assert wellfound_session.capture(search)["fingerprint"] == state["fingerprint"]
            assert not search.evaluate("window.forbidden || false")
            assert value["search_state"]["fingerprint"] == state["fingerprint"]
            for page in owned:
                page.close()
            # Exercise the production supervised child and borrowed-page cleanup.
            helper = folder/"fixture_child.py"
            helper.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0," + repr(str(reader.PROJECT_ROOT)) + ")\nimport url_reader.engine as reader\nreader.BASE_DIR=Path(" + repr(str(folder/"private")) + ")\nfrom url_reader.supervisor import child\nchild(*sys.argv[1:])\n", encoding="utf-8")
            supervised_args = SimpleNamespace(**vars(args))
            supervised_args.output, supervised_args.limit = folder/"supervised.json", 1
            supervised_args.profile, supervised_args.launch = folder/"unused", False
            supervised_args.cdp, supervised_args.workers, supervised_args.retries = cdp, 3, 1
            supervised_args.retry_incomplete = False
            result = {}
            def command(request, reply, stop, registry):
                return [sys.executable, "-u", str(helper), str(request), str(reply), str(stop), str(registry)]
            def execute():
                try:
                    result["value"] = supervised_reader.execute(supervised_args, command_factory=command)
                except BaseException as exc:
                    result["error"] = exc
            worker = threading.Thread(target=execute)
            worker.start()
            deadline = time.monotonic()+30
            while worker.is_alive() and time.monotonic() < deadline:
                search.wait_for_timeout(100)
            if worker.is_alive():
                supervised_args.stop_event.set()
                while worker.is_alive() and time.monotonic() < deadline+10:
                    search.wait_for_timeout(100)
            assert not worker.is_alive(), "Supervised fixture did not finish"
            if "error" in result:
                raise result["error"]
            completed, code = result["value"]
            assert code == 0 and len(completed["jobs"]) == 1, completed
            assert completed["search_state"]["fingerprint"] == state["fingerprint"]
            assert not search.is_closed() and len(context.pages) == 1
            assert len(search_requests) == 1
            # If filters change, the pending posting must not be marked attempted/saved.
            search.goto(SEARCH)
            state = wellfound_session.capture(search)
            args = SimpleNamespace(url=SEARCH, output=folder/"changed.json", fresh=False, limit=2, delay=0, search_state=state)
            changed = {"jobs": [], "errors": []}
            reader.prepare_output(args, changed, SEARCH)
            def change_during_read(url):
                search.locator("#experience").evaluate("el=>el.innerText='3-5 years'")
                return {"link": url, "title": "Should not commit", "description": "Complete description"}
            try:
                reader.collect_jobs(search, SimpleNamespace(read=change_during_read), args, changed, args.output)
            except reader.BrowserStopped as exc:
                assert "filters changed" in str(exc)
            else:
                raise AssertionError("Changed filters did not stop collection")
            assert not changed["jobs"] and not changed["progress"]["attempted_links"]
            assert changed["progress"]["pending_links"] == [JOB1]
            assert wellfound_session.capture(search)["fingerprint"] != state["fingerprint"]
            # Delayed infinite-scroll results must not be mistaken for an end
            # simply because they arrived after the initial one-second wait.
            search.goto(SEARCH)
            search._wellfound_search_state = wellfound_session.capture(search)
            search.get_by_role('button', name='Next page', exact=True).evaluate('el=>el.remove()')
            search.evaluate("setTimeout(()=>document.getElementById('cards').insertAdjacentHTML('beforeend','<a href=/jobs/12347-late>Late job</a>'),2300)")
            outcome = wellfound.next_results(search)
            assert outcome.status == 'advanced' and outcome.method == 'scroll', outcome
            assert len(wellfound.job_links(search)) == 2
            print("Wellfound state fixtures passed: sticky filters and Saved counts stable; every posting in a company card discovered; same-URL Next; no search reload; separate checkpoint scope; three-reader supervised collection; borrowed tab preserved; real filter-change stop retains pending work. All requests intercepted.")
        finally:
            context.close()


if __name__ == "__main__":
    main()
