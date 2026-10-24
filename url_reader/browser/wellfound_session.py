"""Capture and reuse a rendered Wellfound search without copying browser profiles."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

CAPTURE_JS = r'''() => {
    const visible = el => !!el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden';
    const heading = [...document.querySelectorAll('h1')].find(el => visible(el) && /^Search for jobs$/i.test(el.innerText.trim()));
    if (!heading) return null;
    const count = [...document.querySelectorAll('h2,h3,h4,div,p,span')].find(el => visible(el) && /^\d[\d,]*\s+results?$/i.test(el.innerText.trim()));
    if (!count) throw new Error('The filtered Wellfound search has not finished rendering its result count.');
    const top = heading.getBoundingClientRect().bottom, bottom = count.getBoundingClientRect().top;
    const left = Math.min(heading.getBoundingClientRect().left, count.getBoundingClientRect().left) - 1;
    if (bottom <= top) throw new Error('The Wellfound search controls could not be scoped safely.');
    const within = el => visible(el) && el.getBoundingClientRect().left >= left && el.getBoundingClientRect().top >= top && el.getBoundingClientRect().bottom <= bottom + 1;
    const text = [], walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node=walker.nextNode())) {
        if (!node.textContent.trim() || node.parentElement.closest('script,style') || !visible(node.parentElement)) continue;
        const range=document.createRange(); range.selectNodeContents(node);
        const rect=range.getBoundingClientRect();
        if (rect.height && rect.left >= left && rect.top >= top && rect.bottom <= bottom + 1) text.push(node.textContent.trim().replace(/\s+/g,' '));
    }
    const inputs=[...document.querySelectorAll('input,select,textarea')].filter(within).map(el=>({
        label:el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('role') || el.tagName.toLowerCase(),
        value:el.value, checked:['checkbox','radio'].includes(el.type) ? el.checked : null
    }));
    const tabs=[...document.querySelectorAll('[role="tab"],[aria-selected],[aria-current]')].filter(within).map(el=>({
        text:el.innerText.trim(), selected:el.getAttribute('aria-selected'), current:el.getAttribute('aria-current')
    }));
    const header_text=[...text, ...inputs.filter(el=>typeof el.value==='string' && el.value.trim()).map(el=>el.label+': '+el.value.trim())].join(' | ');
    if (!header_text || !inputs.length) throw new Error('Wellfound filter controls could not be captured.');
    return {header_text, inputs, tabs, result_count:Number(count.innerText.replace(/[^0-9]/g,''))};
}'''


def capture(page):
    import url_reader.sources.wellfound as wellfound
    import url_reader.engine as reader
    reader.check_access(page)
    wellfound.search_url(page.url)
    value = page.evaluate(CAPTURE_JS)
    if value is None:
        return None
    identity = {key: value[key] for key in ("header_text", "inputs", "tabs")}
    value.update(mode="open_filtered_tab", url=wellfound.search_url(page.url),
                 fingerprint=hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest())
    return value


def target_id(page):
    session = page.context.new_cdp_session(page)
    try:
        return session.send("Target.getTargetInfo")["targetInfo"]["targetId"]
    finally:
        session.detach()


def find_page(context, identifier, expected):
    import url_reader.engine as reader
    for page in context.pages:
        if reader.source_for_url(page.url) != "wellfound" or reader.canonical_job_url(page.url):
            continue
        if target_id(page) != identifier:
            continue
        actual = capture(page)
        if not actual or actual["fingerprint"] != expected["fingerprint"]:
            raise reader.BrowserStopped("Wellfound filters changed since Start. Saved progress was preserved. Capture the intended search again.")
        return page
    raise reader.BrowserStopped("The selected filtered Wellfound tab is no longer open in reader Chrome. Open it again before resuming.")


def inspect(cdp):
    """Bound DOM inspection in a disposable process, independently of the API thread."""
    try:
        process = subprocess.run([sys.executable, "-m", "url_reader.browser.wellfound_session", "--inspect", cdp],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding="utf-8", timeout=18)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Wellfound tab inspection timed out. Let the search finish loading in reader Chrome, then start again.") from exc
    try:
        value = json.loads(process.stdout)
    except ValueError as exc:
        raise ValueError("Could not inspect reader Chrome's filtered Wellfound tab.") from exc
    if process.returncode:
        raise ValueError(value.get("error", "Could not inspect Wellfound."))
    tabs = value["tabs"]
    if not tabs and value.get("errors"):
        raise ValueError("Wellfound's open search could not be captured: " + value["errors"][0])
    if len(tabs) != 1:
        raise ValueError("Keep exactly one filtered Wellfound search open in reader Chrome, with your filters selected, then start again. Public highlights and your normal browser are separate.")
    return tabs[0]


def inspect_child(cdp):
    import url_reader.engine as reader
    from playwright.sync_api import sync_playwright
    tabs, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp, timeout=10000)
        for context in browser.contexts[:1]:
            for page in context.pages:
                if reader.source_for_url(page.url) != "wellfound" or reader.canonical_job_url(page.url):
                    continue
                try:
                    state = capture(page)
                except (ValueError, reader.PlaywrightError) as exc:
                    errors.append(str(exc).splitlines()[0][:300])
                    continue
                if state:
                    tabs.append({"target": target_id(page), "state": state})
    return {"tabs": tabs, "errors": errors}


def diagnose_job(cdp, url):
    """Read bounded job-layout diagnostics without touching the user's search tab."""
    import url_reader.engine as reader
    from playwright.sync_api import sync_playwright
    if not reader.posting_key(url) or reader.posting_key(url)[0] != "wellfound":
        raise ValueError("Diagnostics require a Wellfound job detail URL.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp, timeout=10000)
        page = browser.contexts[0].new_page()
        page.set_default_timeout(5000)
        try:
            reader.navigate(page, url)
            reader.wait_for_content(page, "h1")
            return page.evaluate(r'''() => ({
                url:location.href,
                headings:[...document.querySelectorAll('h1,h2,h3')].filter(el=>el.getClientRects().length).map(el=>({
                    tag:el.tagName,text:el.innerText,html:el.outerHTML.slice(0,1200),
                    next:el.nextElementSibling?.outerHTML.slice(0,16000),parent:el.parentElement?.outerHTML.slice(0,2500)
                })).slice(0,20),
                company_links:[...document.querySelectorAll('a[href*="/company/"]')].filter(el=>el.getClientRects().length).slice(0,8).map(el=>({text:el.innerText,href:el.getAttribute('href')})),
                descriptions:[...document.querySelectorAll('[id*="description"],[class*="description"],[itemprop="description"]')].filter(el=>el.getClientRects().length).slice(0,8).map(el=>({tag:el.tagName,id:el.id,cls:el.className,text:el.innerText.slice(0,16000)})),
                jsonld_count:document.querySelectorAll('script[type="application/ld+json"]').length
            })''')
        finally:
            page.close()


if __name__ == "__main__":
    try:
        if len(sys.argv) == 4 and sys.argv[1] == "--diagnose-job":
            result = diagnose_job(sys.argv[2], sys.argv[3])
        elif len(sys.argv) == 3 and sys.argv[1] == "--inspect":
            result = inspect_child(sys.argv[2])
        else:
            raise ValueError("Internal Wellfound inspector.")
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(1)
