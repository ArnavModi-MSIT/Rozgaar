"""Offline LinkedIn post fixtures; no external page or clipboard reads."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
import url_reader.engine as reader
import url_reader.sources.linkedin_posts as posts

POST1 = "https://www.linkedin.com/posts/fixture_hiring-share-12345-test/"
POST2 = "https://www.linkedin.com/feed/update/urn:li:activity:12346/"
TEXT = "Hiring freshers.\nFull responsibilities: SQL, Python and reporting.\nApply using the link below."
MODERN = '''<div role="listitem" componentkey="update-card-focusopaque-1FeedType_FLAGSHIP_SEARCH">
<a href="https://www.linkedin.com/in/fixture/"><p>Fixture Recruiter</p></a><p>11m</p>
<button aria-label="Open control menu for post by Fixture Recruiter" onclick="document.getElementById('copy-menu').hidden=false">Menu</button>
<span data-testid="expandable-text-box" style="display:block;max-height:30px;overflow:hidden">
Hiring freshers.<br>Full responsibilities: SQL, Python and reporting.<br>Apply using the link below.
<a href="https://example.test/apply">Application link</a>
<a href="https://www.linkedin.com/posts/other_quoted-share-99999-test/">Quoted link, not this post's permalink</a>
<button aria-hidden="true" data-testid="expandable-text-button" onclick="this.parentElement.style.maxHeight='none';this.remove();window.expanded=true">… more</button></span>
<div class="comments"><span data-testid="expandable-text-box">Unrelated comments<button data-testid="expandable-text-button" onclick="window.wrongClick=true">See more</button></span></div>
<button aria-label="Reaction button state: no reaction" onclick="window.wrongClick=true">Like</button>
<button onclick="window.wrongClick=true">Repost</button>
</div>'''
LEGACY = '''<article data-urn="urn:li:activity:12346"><a class="update-components-actor__name" href="https://www.linkedin.com/in/legacy/">Legacy Recruiter</a>
<div class="feed-shared-inline-show-more-text"><div class="update-components-text">A short preview</div>
<button class="feed-shared-inline-show-more-text__see-more-less-toggle" onclick="const button=this;setTimeout(()=>{button.previousElementSibling.innerText='Complete legacy post text with eligibility and requirements.';button.remove()},200)">...more</button></div>
<article data-urn="urn:li:activity:99998"><div class="update-components-text">Nested repost must not be queued separately.</div></article></article>'''


def fixture(search=False, failed=False):
    modern = MODERN.replace("this.parentElement.style.maxHeight='none';this.remove();window.expanded=true", "void(0)") if failed else MODERN
    menu = '<div id="copy-menu" hidden><p onclick="copyPost()">Copy link to post</p></div>'
    script = '''<script>
window.wrongClick=false;window.expanded=false;window.systemClipboardCalls=0;
navigator.clipboard.writeText=async()=>{window.systemClipboardCalls++;};
navigator.clipboard.write=async()=>{window.systemClipboardCalls++;};
function copyPost() {
    if(!window.expanded)throw new Error('Copied before expanding post');
    navigator.clipboard.writeText(POST_URL); document.getElementById('copy-menu').hidden=true;
}
window.loaded=false;
window.scrollBy=()=>{if(!window.loaded){window.loaded=true;setTimeout(()=>{document.querySelector('main').insertAdjacentHTML('beforeend',LEGACY_CARD)},200);}};
</script>'''.replace("POST_URL", json.dumps(POST1)).replace("LEGACY_CARD", json.dumps(LEGACY))
    return '<main><button onclick="window.wrongClick=true">More</button>' + modern + menu + '</main>' + script


def main():
    chrome = Path(os.environ.get("ProgramFiles", "/nonexistent"))/"Google/Chrome/Application/chrome.exe"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(chrome) if chrome.exists() else None, headless=True)
        try:
            context = browser.new_context(service_workers="block")
            state = {"failed": False, "blocked": False}
            def route(request):
                assert request.request.method == "GET", "A post fixture attempted a submission"
                url = request.request.url
                if "/search/results/content/" in url:
                    body = '<script>history.replaceState(null,"","/uas/login")</script>' if state["blocked"] else fixture(search=True)
                elif "12346" in url:
                    body = '<main>' + LEGACY + '</main><script>window.wrongClick=false</script>'
                else:
                    body = fixture(failed=state["failed"])
                request.fulfill(content_type="text/html", body=body)
            context.route("**/*", route)
            page, detail = context.new_page(), context.new_page()
            reader.navigate(page, posts.DEFAULT_SEARCH)
            assert reader.collect_links(page, 10) == [POST1]
            assert page.evaluate("window.expanded")
            assert page.evaluate("window.systemClipboardCalls") == 0
            assert "__jobReaderPostLink" not in page.evaluate("Object.keys(window)")
            record = reader.read_job(detail, POST1)
            assert record["source"] == "linkedin_posts" and record["record_type"] == "post", record
            assert record["author"] == "Fixture Recruiter" and record["post_id"] == "share:12345", record
            assert record["description_expanded"] is True and record["description_status"] == "complete_candidate", record
            assert "Full responsibilities" in record["description"] and "Unrelated comments" not in record["description"], record
            assert "https://example.test/apply" in record["external_links"]
            assert not detail.evaluate("window.wrongClick")
            assert reader.next_results(page).status == "advanced"
            assert reader.job_links(page) == [POST1, POST2]
            legacy = reader.read_job(detail, POST2)
            assert "Complete legacy post text" in legacy["description"] and legacy["description_expanded"]
            # Stop/resume skips a saved alias identity and collects only the next post.
            result = {"search_url": reader.search_url(posts.DEFAULT_SEARCH), "jobs": [record], "errors": [],
                      "progress": {"results_page_url": reader.search_url(posts.DEFAULT_SEARCH), "pending_links": [],
                                   "attempted_links": [POST1], "page_complete": True}}
            with tempfile.TemporaryDirectory(dir=reader.BASE_DIR) as folder:
                reader.collect_jobs(page, SimpleNamespace(read=lambda url: reader.read_job(detail, url)),
                                    SimpleNamespace(limit=2, delay=0), result, Path(folder)/"posts.json")
                saved = json.loads((Path(folder)/"posts.json").read_text(encoding="utf-8"))
            assert result["status"] == "completed" and len(saved["jobs"]) == 2, result
            assert not page.evaluate("window.wrongClick")
            state["failed"] = True
            record = reader.read_job(detail, POST1)
            assert record["description_status"] == "suspected_truncated" and not record["description_expanded"], record
            state["blocked"] = True
            try:
                reader.navigate(page, posts.DEFAULT_SEARCH)
            except reader.AccessBlocked:
                pass
            else:
                raise AssertionError("Login was not detected")
            print("LinkedIn posts fixtures passed: scoped More expansion, equal-length hidden text, opaque-card Copy link without system clipboard writes, legacy posts, nested repost exclusion, scrolling, resume, warnings and login stop.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
