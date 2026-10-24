"""Production watchdog against an isolated Chrome with intercepted stalled pages."""
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
from tests.reader.instahyre_browser_smoke import SEARCH_HTML, DETAIL_HTML

LINKEDIN_SEARCH = "https://www.linkedin.com/jobs/search/?keywords=fixture"
LINKEDIN_DETAIL = '''<h1 class="top-card-layout__title">Fixture analyst</h1>
<a class="topcard__org-name-link">Fixture</a><section class="jobs-description">
<div class="jobs-description-content__text">Complete SQL and Python responsibilities, qualifications and internship details.</div></section>'''


def main():
    chrome = Path(os.environ.get("ProgramFiles", "/nonexistent"))/"Google/Chrome/Application/chrome.exe"
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder, sync_playwright() as p:
        folder = Path(folder)
        context = p.chromium.launch_persistent_context(str(folder/"chrome"), executable_path=str(chrome) if chrome.exists() else None,
            headless=True, service_workers="block", args=[f"--remote-debugging-port={port}", "--remote-debugging-address=127.0.0.1"])
        original = context.pages[0]
        blocked_routes = []
        requests = []
        def route(request):
            assert request.request.method == "GET", "Fixture attempted a submission"
            url = request.request.url
            requests.append(url)
            if url.endswith("/stall.js"):
                blocked_routes.append(request)  # Deliberately never finish the deferred script.
                return
            if url == "https://wellfound.com/jobs":
                body = '<a href="/jobs/9001-fixture">Fixture job</a>'
            elif "wellfound.com/jobs/9001" in url:
                body = '<h1>Fixture analyst</h1><a href="/company/fixture">Fixture</a><div id="job-description">Complete SQL and Python responsibilities and qualifications.</div>'
            elif "/jobs/search" in url:
                body = '<div class="jobs-search-results-list"><a href="/jobs/view/123/">First</a><a href="/jobs/view/456/">Second</a></div>'
            elif "/candidate/opportunities/" in url:
                body = SEARCH_HTML
            elif "/job-12345" in url:
                body = DETAIL_HTML
            else:
                body = LINKEDIN_DETAIL
                if "/456/" in url or "/job-12346" in url:
                    body = '<script defer src="/stall.js"></script>' + body
            request.fulfill(content_type="text/html", body=body)
        context.route("**/*", route)
        try:
            # Override only private test storage in the child, using the production runner.
            helper = folder/"fixture_child.py"
            helper.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0," + repr(str(reader.PROJECT_ROOT)) + ")\nimport url_reader.engine as reader\nreader.BASE_DIR=Path(" + repr(str(folder/"private")) + ")\nfrom url_reader.supervisor import child\nchild(*sys.argv[1:])\n", encoding="utf-8")
            for source, search, stalled in (("wellfound", "https://wellfound.com/jobs", False), ("linkedin", LINKEDIN_SEARCH, True), ("instahyre", reader.instahyre.DEFAULT_SEARCH, True)):
                output = folder/f"{source}.json"
                args = SimpleNamespace(url=search, output=output, profile=folder/"unused", fresh=False, limit=2 if stalled else 1,
                    delay=0, workers=1 if stalled else 3, retries=1, retry_incomplete=False, launch=False,
                    cdp=f"http://127.0.0.1:{port}", stop_event=threading.Event())
                result = {}
                def command(request, reply, stop, registry):
                    return [sys.executable, "-u", str(helper), str(request), str(reply), str(stop), str(registry)]
                def execute():
                    try:
                        result["value"] = supervised_reader.execute(args, idle_timeout=10, command_factory=command)
                    except BaseException as exc:
                        result["error"] = exc
                worker = threading.Thread(target=execute)
                worker.start()
                deadline = time.monotonic()+55
                while worker.is_alive() and time.monotonic() < deadline:
                    original.wait_for_timeout(100)  # Pump the owning Playwright fixture connection.
                if worker.is_alive():
                    args.stop_event.set()
                    while worker.is_alive() and time.monotonic() < deadline+10:
                        original.wait_for_timeout(100)
                assert not worker.is_alive(), "Supervisor did not finish within its hard bound"
                if "error" in result:
                    raise result["error"]
                value, code = result["value"]
                assert (code, value["status"]) == ((1, "partial") if stalled else (0, "completed")), value
                assert len(value["jobs"]) == 1 and value["jobs"][0]["source"] == source, value
                if stalled:
                    assert value["progress"]["pending_links"], value
                    assert value["browser_recoveries"] == 1, value
                saved = json.loads(output.read_text(encoding="utf-8"))
                assert saved["jobs"] == value["jobs"], saved
                if stalled:
                    assert saved["progress"]["pending_links"], saved
                original.wait_for_timeout(100)
                assert not original.is_closed() and len(context.pages) == 1, len(context.pages)
                print(f"{source}: " + ("hung renderer stopped, one recovery attempted, saved/pending work retained" if stalled else "three-reader supervised run completed") + "; owned tabs cleaned up and original tab preserved.", flush=True)
            assert blocked_routes and requests
            print("Stall browser fixtures passed. All job-site requests were intercepted; no personal history or profile was used.")
        finally:
            for pending in blocked_routes:
                try:
                    pending.abort()
                except reader.PlaywrightError:
                    pass
            context.unroute_all(behavior="ignoreErrors")
            context.close()


if __name__ == "__main__":
    main()
