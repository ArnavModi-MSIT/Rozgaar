"""Read LinkedIn content-search posts after expanding their own More control."""
import argparse
import json
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from url_reader.quality import annotate
from url_reader.identity import canonical_job_url, posting_key

HOSTS = {"linkedin.com", "www.linkedin.com"}
DEFAULT_SEARCH = "https://www.linkedin.com/search/results/content/?keywords=%23fresherhiring&origin=GLOBAL_SEARCH_HEADER&sortBy=%5B%22date_posted%22%5D"
CARD = '[role="listitem"][componentkey^="update-card-focus"], [data-urn^="urn:li:activity:"], [data-urn^="urn:li:share:"], [data-urn^="urn:li:ugcPost:"]'
TEXT = '[data-testid="expandable-text-box"], .update-components-text, .feed-shared-update-v2__description, .feed-shared-text__text-view'
MORE = 'button[data-testid="expandable-text-button"], button.feed-shared-inline-show-more-text__see-more-less-toggle, button.see-more, button[aria-label="See more"], button[aria-label="Show more"]'
RESULT_ITEM = CARD
SCROLL_WAIT_SECONDS = 15


def search_url(value):
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.password
            or parts.port not in (None, 443) or parts.path.rstrip("/") != "/search/results/content"):
        raise argparse.ArgumentTypeError("Use a LinkedIn /search/results/content/ post-search URL.")
    params = [(key, item) for key, item in parse_qsl(parts.query) if key not in {"page", "start", "sortBy"}]
    params.append(("sortBy", json.dumps(["date_posted"], separators=(",", ":"))))
    return urlunsplit(("https", "www.linkedin.com", "/search/results/content/", urlencode(params), ""))


def cards(page):
    # Exclude quoted/reposted cards nested inside the outer result.
    return [card for card in page.locator(CARD).all() if card.is_visible()]


def card_token(card):
    return card.get_attribute("data-urn") or card.get_attribute("componentkey") or ""


def outer_card(card):
    return not card.evaluate("(el, selector) => Boolean(el.parentElement?.closest(selector))", CARD)


def direct_link(card):
    urn = card.get_attribute("data-urn") or ""
    values = ["https://www.linkedin.com/feed/update/" + urn + "/"] if urn else []
    values += card.locator('a[href*="/feed/update/"], a[href*="/posts/"]').evaluate_all(
        "(els, textSelector)=>els.filter(el=>!el.closest(textSelector)).map(el=>el.href)", TEXT)
    for value in values:
        key = posting_key(value)
        if key and key[0] == "linkedin_posts":
            return canonical_job_url(value)
    return None


def text_region(card):
    for node in card.locator(TEXT).all():
        if node.is_visible() and node.evaluate("""(el, args) => {
            const owner=el.closest(args.selector);
            const token=owner?.getAttribute('data-urn') || owner?.getAttribute('componentkey') || '';
            return token===args.token && !el.closest('.comments, .comments-comment-item, .comments-comments-list, [data-testid="comment"]');
        }""", {"selector": CARD, "token": card_token(card)}):
            return node
    return None


def text_of(card):
    node = text_region(card)
    if node is not None:
        # Read only the post commentary, excluding More/less button labels.
        return node.evaluate("""el => {
                const clone=el.cloneNode(true);
                clone.querySelectorAll('button,[role="button"],script,style').forEach(n=>n.remove());
                clone.querySelectorAll('br').forEach(n=>n.replaceWith(document.createTextNode('\\n')));
                clone.querySelectorAll('p,div,li').forEach(n=>n.append(document.createTextNode('\\n')));
                return clone.textContent.trim();
        }""")
    return ""


def more_controls(card):
    region = text_region(card)
    if region is None:
        return []
    wrapper = region.locator('xpath=ancestor::*[contains(concat(" ",normalize-space(@class)," ")," feed-shared-inline-show-more-text ")][1]')
    if wrapper.count():
        region = wrapper
    # Keep expansion inside the first own commentary, away from comments and quotes.
    known = region.locator(MORE).all()
    known += region.get_by_role("button", name=re.compile(r"^\s*(?:(?:\u2026|\.{3})\s*)?(?:(?:see|show)\s+)?more\s*$", re.I)).all()
    return [control for control in known if control.is_visible() and control.is_enabled()]


def expand_post(page, card):
    import url_reader.engine as reader
    expanded = False
    for _ in range(3):
        reader.check_cancel(vars(page).get("_reader_stop_event"))
        controls = more_controls(card)
        if not controls:
            break
        before = text_of(card)
        controls[0].click(timeout=5000)
        for _ in range(20):
            reader.interruptible_wait(page, 250)
            reader.check_access(page)
            # The modern layout already contains hidden full text; disappearance
            # of the visible More control confirms expansion even if length is equal.
            if not more_controls(card):
                expanded = True
                break
        else:
            return expanded, True
        if text_of(card) == before and more_controls(card):
            break
    return expanded, bool(more_controls(card))


CAPTURE_START = """() => {
    const clipboard=navigator.clipboard;
    const state=window.__jobReaderPostLink={value:null,restore:()=>{}};
    const oldText=clipboard?.writeText, oldWrite=clipboard?.write, oldExec=document.execCommand;
    if(clipboard) {
        clipboard.writeText=text=>{state.value=String(text);return Promise.resolve();};
        clipboard.write=async items=>{for(const item of items)if(item.types.includes('text/plain'))
            state.value=await(await item.getType('text/plain')).text();};
    }
    document.execCommand=function(command,...args) {
        if(String(command).toLowerCase()==='copy') {
            state.value=document.activeElement?.value || window.getSelection().toString(); return true;
        }
        return oldExec.call(this,command,...args);
    };
    state.restore=()=>{if(clipboard){clipboard.writeText=oldText;clipboard.write=oldWrite;}document.execCommand=oldExec;};
}"""


def resolve_copied_link(page, value):
    key = posting_key(value)
    if key and key[0] == "linkedin_posts":
        return canonical_job_url(value)
    for _ in range(3):
        parts = urlsplit(value or "")
        if (parts.scheme != "https" or parts.hostname != "lnkd.in" or parts.username or parts.password
                or parts.port not in (None, 443) or not parts.path.startswith("/p/")):
            raise ValueError("Copy link did not return a valid LinkedIn post permalink.")
        response = page.context.request.get(value, max_redirects=0, timeout=10000)
        try:
            if response.status in {401, 403, 429}:
                import url_reader.engine as reader
                raise reader.AccessBlocked(f"LinkedIn post permalink returned HTTP {response.status}.")
            if response.status not in {301, 302, 303, 307, 308}:
                break
            value = urljoin(value, response.headers.get("location", ""))
        finally:
            response.dispose()
        key = posting_key(value)
        if key and key[0] == "linkedin_posts":
            return canonical_job_url(value)
    raise ValueError("LinkedIn's copied short permalink could not be resolved to a post.")


def copy_link(page, card):
    import url_reader.engine as reader
    page.evaluate(CAPTURE_START)
    try:
        menu = card.get_by_role("button", name=re.compile(r"^(?:Open control menu for post|More actions)", re.I))
        if not menu.count():
            raise ValueError("No stable post ID or Copy link control found on this result.")
        menu.first.click(timeout=5000)
        page.locator(':text-is("Copy link to post"):visible').first.click(timeout=8000, no_wait_after=True)
        value = None
        for _ in range(20):
            reader.interruptible_wait(page, 100)
            value = page.evaluate("window.__jobReaderPostLink.value")
            if value:
                break
        return resolve_copied_link(page, value)
    finally:
        page.evaluate("() => {window.__jobReaderPostLink?.restore();delete window.__jobReaderPostLink;}")
        page.keyboard.press("Escape")


def job_links(page):
    values = list(vars(page).get("_reader_post_cache", {}).values())
    for card in cards(page):
        if outer_card(card) and (link := direct_link(card)):
            values.append(link)
    unique = {}
    for link in values:
        unique.setdefault(posting_key(link), link)
    return list(unique.values())


def collect_links(page, limit, stop_event=None):
    import url_reader.engine as reader
    reader.check_cancel(stop_event)
    reader.check_access(page)
    page.bring_to_front()
    cache = vars(page).setdefault("_reader_post_cache", {})
    for card in cards(page):
        reader.check_cancel(stop_event or vars(page).get("_reader_stop_event"))
        if not outer_card(card):
            continue
        token = card_token(card)
        if token and token in cache:
            continue
        # Expand on the result itself before queuing its permalink.
        expand_post(page, card)
        link = direct_link(card) or copy_link(page, card)
        cache[token or link] = link
    return job_links(page)


def next_results(page):
    import url_reader.engine as reader
    from url_reader.browser.pagination import PaginationResult, advance
    before = set(job_links(page))
    controls = [page.get_by_role("button", name=re.compile(r"^(?:Next|Show more results|See more results)\b", re.I)),
                page.locator('a[rel="next"], button[aria-label="Next"]')]
    if any(control.is_visible() for group in controls for control in group.all()):
        outcome = advance(page, controls, lambda current: collect_links(current, 1000), prefer_click=True)
        if outcome:
            return outcome
    for _ in range(SCROLL_WAIT_SECONDS * 2):
        reader.check_cancel(vars(page).get("_reader_stop_event"))
        reader.check_access(page)
        page.evaluate("""selector => {
            const all=[...document.querySelectorAll(selector)].filter(el=>el.getClientRects().length);
            const last=all[all.length-1]; if(last)last.scrollIntoView({block:'end'});
            let root=last?.parentElement;
            while(root&&root!==document.body) {
                if(root.scrollHeight>root.clientHeight+2&&/auto|scroll/.test(getComputedStyle(root).overflowY)) {
                    root.scrollBy(0,Math.max(500,root.clientHeight)); return;
                } root=root.parentElement;
            }
            window.scrollBy(0,Math.max(500,innerHeight));
        }""", CARD)
        reader.interruptible_wait(page, 500)
        after = set(collect_links(page, 1000))
        if after - before:
            return PaginationResult("advanced", page.url, len(after), navigation_attempted=True, method="scroll")
    return PaginationResult("scroll_idle", page.url, len(before), navigation_attempted=True,
                            error="No new post permalinks appeared after scrolling and waiting.", method="scroll")


def read_job(page, url):
    import url_reader.engine as reader
    reader.navigate(page, url)
    reader.wait_for_content(page, CARD)
    expected = posting_key(url)
    candidates = [card for card in cards(page) if outer_card(card)]
    exact = next((card for card in candidates if posting_key(direct_link(card)) == expected), None)
    # On the modern permalink page the main post has an opaque component key.
    card = exact if exact is not None else next((card for card in candidates
        if (card.get_attribute("componentkey") or "").startswith("update-card-focus")), None)
    if card is None:
        raise ValueError("The requested LinkedIn post container was not found.")
    reader.wait_for_content(page, TEXT)
    expanded, pending = expand_post(page, card)
    text = text_of(card)
    if not text:
        raise ValueError("No post text was found; no empty post was saved.")
    author = reader.first_text(card, ".update-components-actor__name, .feed-shared-actor__name")
    author_url = ""
    for anchor in card.locator('a[href*="/in/"], a[href*="/company/"]').all():
        if anchor.is_visible() and anchor.inner_text().strip():
            author = author or anchor.inner_text().strip().split("\n")[0]
            author_url = anchor.get_attribute("href") or ""
            break
    posted = reader.first_text(card, "time, .update-components-actor__sub-description, .feed-shared-actor__sub-description")
    if not posted:
        posted = next((line.strip() for line in card.inner_text().splitlines()
                       if re.fullmatch(r"[0-9]+\s*(?:s|m|h|d|w|mo|yr)(?:\s*[•·].*)?", line.strip())), "")
    external = text_region(card).locator('a[href]').evaluate_all("""els=>els.map(el=>el.href)
        .filter(value=>/^(https?:|mailto:)/.test(value)&&!/^https?:\\/\\/(?:www\\.)?linkedin\\.com\\//.test(value))""")
    return annotate({"source": "linkedin_posts", "record_type": "post", "job_id": expected[1], "post_id": expected[1],
                     "link": canonical_job_url(url), "title": text.splitlines()[0][:180], "company": author,
                     "author": author, "author_profile": author_url, "posted_at_text": posted,
                     "location_and_posting_info": posted, "description": text,
                     "external_links": list(dict.fromkeys(external)), "description_expanded": expanded,
                     "extraction_method": "scoped_post_dom", "collected_at": datetime.now(timezone.utc).isoformat()},
                    expansion_pending=pending)
