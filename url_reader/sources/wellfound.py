"""Wellfound public and signed-in searches with scoped job descriptions."""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from url_reader.quality import annotate
from url_reader.identity import canonical_job_url, posting_key

DEFAULT_SEARCH = "https://wellfound.com/jobs"
INDIA_SEARCH = "https://wellfound.com/location/india"
HOSTS = {"wellfound.com", "www.wellfound.com"}
RESULT_ITEM = 'a[href*="/jobs/"]:not(footer a):not(nav a)'
DESCRIPTION = '#job-description, div[class^="styles_description__"], div[class*=" styles_description__"]'


def search_url(value):
    try:
        parts = urlsplit(value)
        path = parts.path.rstrip("/")
        valid = (parts.scheme == "https" and parts.hostname in HOSTS
                 and not parts.username and not parts.password and parts.port in (None, 443)
                 and re.fullmatch(r"/(?:jobs|location/[\w%-]+|role/(?:l/[\w%-]+/)?[\w%-]+|company/[\w%-]+/jobs)", path))
    except ValueError:
        valid = False
    if not valid:
        raise argparse.ArgumentTypeError("Use a Wellfound /jobs, /location/..., /role/... or /company/.../jobs results URL.")
    # Keep all filters, including repeated and blank values; reset only pagination.
    params = [(key, item) for key, item in parse_qsl(parts.query, keep_blank_values=True) if key != "page"]
    return urlunsplit(("https", "wellfound.com", path, urlencode(params), ""))


def job_links(page):
    """Keep each posting ID, including multiple job rows in one company card."""
    values = page.locator(RESULT_ITEM).evaluate_all("els => els.filter(el => el.getClientRects().length).map(el => el.href)")
    unique = {}
    for value in values:
        key = posting_key(value)
        if key and key[0] == "wellfound":
            unique.setdefault(key, canonical_job_url(value))
    return list(unique.values())


def collect_links(page, limit, stop_event=None):
    import url_reader.engine as reader
    reader.check_cancel(stop_event)
    reader.check_access(page)
    verify_search_state(page)
    return job_links(page)


def verify_search_state(page):
    import url_reader.engine as reader
    from url_reader.browser.wellfound_session import capture
    expected = vars(page).get("_wellfound_search_state")
    if expected:
        current = capture(page)
        if not current or current["fingerprint"] != expected["fingerprint"]:
            raise reader.BrowserStopped("Wellfound search filters changed during collection. Saved jobs and pending links were preserved. Start again with the intended filters.")
    elif any(re.fullmatch(r"Search for jobs", text.strip(), re.I) for text in page.locator("h1").all_inner_texts()):
        raise reader.BrowserStopped("This Wellfound search keeps filters in browser state. Enable open filtered tab mode and set the filters in reader Chrome before collecting.")


def next_results(page):
    import url_reader.engine as reader
    from url_reader.browser.pagination import advance, PaginationResult
    verify_search_state(page)
    live = bool(vars(page).get("_wellfound_search_state"))
    before = set(job_links(page))
    page.evaluate("window.scrollTo(0, document.scrollingElement.scrollHeight)")
    reader.interruptible_wait(page, 1000)
    reader.check_access(page)
    verify_search_state(page)
    after = set(job_links(page))
    if after - before:
        return PaginationResult("advanced", page.url, len(after), method="scroll")
    controls = page.locator('a[rel="next"], a[aria-label="Next page"], button[aria-label="Next page"]')
    if live:
        controls = controls.or_(page.get_by_role("button", name=re.compile(r"^(?:Next(?: page)?|Load more(?: jobs)?|Show more(?: jobs)?)$", re.I)))
    result = advance(page, [controls], job_links, timeout=40, results_timeout=20, prefer_click=live)
    verify_search_state(page)
    if live and result.status == "missing_control":
        # Infinite-scroll responses may arrive after the first one-second wait.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            reader.check_cancel(vars(page).get("_reader_stop_event"))
            reader.interruptible_wait(page, 250)
            reader.check_access(page)
            verify_search_state(page)
            current = set(job_links(page))
            if current - before:
                return PaginationResult("advanced", page.url, len(current), method="scroll")
        result.status = "scroll_idle"
    if result.status == "missing_control":
        for text in page.locator("h4").all_inner_texts():
            count = re.fullmatch(r"\s*Page\s+(\d+)\s+of\s+(\d+)\s*", text, re.I)
            if count and int(count[1]) == int(count[2]) and int(count[1]) > 0:
                result.status, result.method = "verified_last_page", "page_count"
                break
        landing_heading = page.get_by_role("heading", name=re.compile(r"^Trending startup jobs$", re.I))
        curated = any(heading.is_visible() for heading in landing_heading.all())
        if urlsplit(page.url).path.rstrip("/") == "/jobs" and curated and result.status == "missing_control":
            result.status = "curated_list_end"
            result.method = "curated_jobs_page"
            result.error = ""
    return result


class _DescriptionText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if not self.hidden and tag in {"p", "div", "li", "br", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden and tag in {"p", "div", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def description_text(value):
    parser = _DescriptionText()
    parser.feed(value if isinstance(value, str) else "")
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def jobposting_data(scripts, url):
    """Select only the requested posting, never a recommended job's JSON-LD."""
    jobs = []
    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            types = value.get("@type", [])
            if types == "JobPosting" or isinstance(types, list) and "JobPosting" in types:
                jobs.append(value)
            visit(value.get("@graph"))
    for script in scripts:
        try:
            visit(json.loads(script))
        except (ValueError, TypeError):
            continue
    expected = posting_key(url)
    for job in jobs:
        identifier = job.get("identifier")
        identifier = identifier.get("value") if isinstance(identifier, dict) else identifier
        if (expected and str(identifier) == expected[1]) or (expected and posting_key(job.get("url")) == expected):
            return job
    if len(jobs) == 1 and not jobs[0].get("identifier") and not jobs[0].get("url"):
        return jobs[0]
    return {}


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def location_text(job):
    values = job.get("jobLocation", [])
    values = values if isinstance(values, list) else [values]
    locations = []
    for value in values:
        address = value.get("address", {}) if isinstance(value, dict) else {}
        if isinstance(address, dict):
            country = address.get("addressCountry", "")
            country = country.get("name", "") if isinstance(country, dict) else country
            location = ", ".join(dict.fromkeys(filter(None, [_text(address.get("addressLocality")), _text(address.get("addressRegion")), _text(country)])))
            if location:
                locations.append(location)
    if job.get("jobLocationType") == "TELECOMMUTE":
        locations.insert(0, "Remote")
    return "; ".join(dict.fromkeys(locations))


def salary_text(value):
    if not isinstance(value, dict):
        return _text(value)
    amount = value.get("value", {})
    if not isinstance(amount, dict):
        return " ".join(str(item) for item in (value.get("currency"), amount) if item is not None)
    numbers = [str(amount[key]) for key in ("minValue", "maxValue") if amount.get(key) is not None]
    if not numbers and amount.get("value") is not None:
        numbers = [str(amount["value"])]
    return " ".join(filter(None, [_text(value.get("currency")), " – ".join(numbers), _text(amount.get("unitText"))]))


def scoped_description(page):
    return page.evaluate(r'''selector => {
        const visible=el=>!!el.getClientRects().length;
        const exact=document.querySelector('#job-description');
        if (exact && visible(exact) && exact.innerText.trim()) return {text:exact.innerText.trim(),method:'scoped_dom'};
        // The signed-in detail page uses a CSS-module description, without JSON-LD.
        // Exclude company/recommendation summaries after the primary description.
        const boundary=[...document.querySelectorAll('h2,h3')].find(el=>visible(el) && /^(?:Similar jobs\b|About\s+\S|Jobs at\b)/i.test(el.innerText.trim()));
        const candidates=[...document.querySelectorAll(selector)].filter(el=>visible(el) && !el.closest('nav,footer')
            && (!boundary || (el.compareDocumentPosition(boundary)&Node.DOCUMENT_POSITION_FOLLOWING)))
            .map(el=>el.innerText.trim()).filter(Boolean);
        candidates.sort((a,b)=>b.length-a.length);
        return {text:candidates[0] || '',method:'signed_in_dom'};
    }''', DESCRIPTION)


def read_job(page, url):
    import url_reader.engine as reader
    reader.navigate(page, url)
    reader.wait_for_content(page, "h1")
    for attempt in range(21):
        reader.check_cancel(vars(page).get("_reader_stop_event"))
        reader.check_access(page)
        structured = jobposting_data(page.locator('script[type="application/ld+json"]').all_text_contents(), url)
        title = _text(structured.get("title")) or reader.first_text(page, "h1")
        organization = structured.get("hiringOrganization", {})
        company = _text(organization.get("name")) if isinstance(organization, dict) else ""
        company = company or reader.first_text(page, 'a[href^="/company/"]:not(footer a):not(nav a)')
        dom = scoped_description(page)
        full_description = description_text(structured.get("description"))
        description, method = (full_description, "jobposting_jsonld") if len(full_description) > len(dom["text"]) else (dom["text"], dom["method"])
        if title and company and description:
            break
        if attempt < 20:
            reader.interruptible_wait(page, 500)
    if not title or not company or not description:
        missing = [field for field, value in (("title", title), ("company", company), ("description", description)) if not value]
        raise ValueError("Wellfound title, company or description was missing after waiting for rendering (missing: " + ", ".join(missing) + "); no empty listing was saved.")
    suffix = " at " + company
    if title.casefold().endswith(suffix.casefold()):
        title = title[:-len(suffix)].strip()
    location = location_text(structured)
    salary = salary_text(structured.get("baseSalary"))
    employment = structured.get("employmentType", "")
    employment = ", ".join(filter(None, map(_text, employment))) if isinstance(employment, list) else _text(employment)
    # Visible header also covers pages without structured salary/location metadata.
    header = reader.first_text(page, "h1 + ul")
    if method == "signed_in_dom" and not header:
        header = page.locator("h1").first.locator("xpath=..").inner_text().strip()
    return annotate({"source": "wellfound", "job_id": posting_key(url)[1], "link": canonical_job_url(page.url),
                     "title": title, "company": company, "description": description,
                     "location": location, "salary": salary, "employment_type": employment,
                     "location_and_posting_info": "\n".join(filter(None, [location, salary, employment, header])),
                     "date_posted": _text(structured.get("datePosted")), "valid_through": _text(structured.get("validThrough")),
                     "extraction_method": method, "collected_at": datetime.now(timezone.utc).isoformat()})
