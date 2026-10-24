"""Instahyre Search Results adapter using rendered controls and public job pages."""
import argparse
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, parse_qs, urlencode, urlsplit, urlunsplit

from url_reader.quality import annotate
from url_reader.identity import canonical_job_url, posting_key

HOSTS = {"instahyre.com", "www.instahyre.com"}
DEFAULT_SEARCH = "https://www.instahyre.com/candidate/opportunities/?company_size=0&job_type=0&search=true&years=0"
RESULT_ITEM = ".tab.selected"
CARDS = "a#employer-profile-opportunity"
DESCRIPTION = ".profile-content.job-description"


def search_url(value):
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.password
            or parts.port not in (None, 443) or parts.path.rstrip("/") != "/candidate/opportunities"):
        raise argparse.ArgumentTypeError("Use an Instahyre /candidate/opportunities/ Search Results URL.")
    params = parse_qsl(parts.query)
    if any(key in {"matching", "interested", "uninterested", "applied"} and item.lower() == "true"
           for key, item in params):
        raise argparse.ArgumentTypeError("Use Instahyre Search Results, rather than a saved opportunity category.")
    params = [(key, item) for key, item in params if key not in {"page", "offset", "search"}]
    for key, default, allowed in (("company_size", "0", {"0", "1", "2", "3"}),
                                  ("job_type", "0", {"0", "1", "2"})):
        values = [item for name, item in params if name == key]
        if not values:
            params.append((key, default))
        elif len(values) != 1 or values[0] not in allowed:
            raise argparse.ArgumentTypeError(f"Invalid Instahyre {key} filter.")
    years = [item for key, item in params if key == "years"]
    if years and (len(years) != 1 or not re.fullmatch(r"(?:[0-9]|1[0-9]|2[0-5])", years[0])):
        raise argparse.ArgumentTypeError("Instahyre years must be an integer from 0 to 25.")
    return urlunsplit(("https", "www.instahyre.com", "/candidate/opportunities/", urlencode(params + [("search", "true")]), ""))


def search_active(page):
    if parse_qs(urlsplit(page.url).query).get("search") != ["true"]:
        return False
    return any(re.match(r"^\s*Search Results\b", text) for text in page.locator(".tab.selected:visible").all_inner_texts())


def require_search(page):
    import url_reader.engine as reader
    reader.check_access(page)
    if not search_active(page):
        raise ValueError("Instahyre Search Results is not selected; no opportunity category was collected.")


def wait_search_ready(page):
    import url_reader.engine as reader
    started = time.monotonic()
    previous = None
    stable = 0
    for _ in range(40):
        reader.check_cancel(vars(page).get("_reader_stop_event"))
        reader.check_access(page)
        if (search_active(page) and not page.locator(".tab.selected .fa-spinner:visible").count()
                and not page.locator(".ng-leave:visible").count()):
            current = tuple(job_links(page))
            stable = stable + 1 if current == previous else 0
            previous = current
            if stable >= 2 and time.monotonic() - started >= 1:
                return
        else:
            previous, stable = None, 0
        reader.interruptible_wait(page, 250)
    raise reader.TransientReadError("Instahyre Search Results did not finish loading; progress was kept.")


def navigate_search(page, url):
    import url_reader.engine as reader
    requested = search_url(url)
    reader.navigate_page(page, requested, verify_search=False)
    reader.wait_for_content(page, ".skills-search-btn, .tab.selected")
    if not search_active(page):
        # A fresh opportunities tab can reset the supplied URL to Recommended.
        page.get_by_role("button", name="Search", exact=True).click(timeout=5000)
    wait_search_ready(page)
    desired = dict(parse_qsl(urlsplit(requested).query))
    for key in ("company_size", "job_type"):
        if parse_qs(urlsplit(page.url).query).get(key, ["0"]) != [desired[key]]:
            control = page.locator(f'input[ng-click*="search.searchObj.{key} = {desired[key]};"]:visible').first
            if not control.count():
                raise ValueError(f"Instahyre {key} control changed; search filters were not restored.")
            control.click(timeout=5000)
            wait_search_ready(page)
    if "years" in desired and parse_qs(urlsplit(page.url).query).get("years") != [desired["years"]]:
        track = page.locator(".slider-track:visible").first
        track.scroll_into_view_if_needed(timeout=5000)
        bounds = track.bounding_box()
        if not bounds:
            raise ValueError("Instahyre experience slider was not available.")
        years = int(desired["years"])
        if years:
            section = track.locator("xpath=../..").inner_text()
            maximum = re.search(r"([0-9]+)\+", section)
            if not maximum:
                raise ValueError("Instahyre experience range could not be verified.")
            x = 6 + (bounds["width"] - 12) * years / (int(maximum.group(1)) + 1)
        else:
            x = 1
        track.click(position={"x": min(bounds["width"] - 1, max(1, x)), "y": bounds["height"] / 2}, timeout=5000)
        wait_search_ready(page)
    require_search(page)
    if reader.search_signature(requested) != reader.search_signature(page.url):
        raise ValueError("Instahyre did not retain the supplied search filters; no listings were collected. Run Search on Instahyre and copy its resulting URL.")


def job_links(page):
    if not search_active(page):
        return []
    raw = page.locator(CARDS).evaluate_all("""els => {
        const urls=[];
        for (const el of els) {
            if (!el.getClientRects().length || el.closest('.ng-leave')) continue;
            if (el.href) { urls.push(el.href); continue; }
            const node=el.querySelector('[id^="job-skills-"]');
            const id=node && /^job-skills-([0-9]+)$/.exec(node.id);
            if(id) urls.push('https://www.instahyre.com/job-'+id[1]+'/');
        }
        return urls;
    }""")
    unique = {}
    for value in raw:
        key = posting_key(value)
        if key and key[0] == "instahyre":
            unique.setdefault(key, canonical_job_url(value))
    return list(unique.values())


def collect_links(page, limit, stop_event=None):
    import url_reader.engine as reader
    reader.check_cancel(stop_event)
    require_search(page)
    wait_search_ready(page)
    return job_links(page)


def next_results(page):
    import url_reader.engine as reader
    from url_reader.browser.pagination import advance, PaginationResult
    require_search(page)
    wait_search_ready(page)
    # Instahyre changes cards via its visible li controls; the URL stays unchanged.
    next_control = page.locator(".pagination li").filter(has_text=re.compile(r"^\s*Next\b", re.I))
    visible = any(control.is_visible() for control in next_control.all())
    if not visible:
        text = page.locator("body").inner_text()
        counts = re.search(r"Showing\s+([0-9,]+)\s*[-–]\s*([0-9,]+)\s+out of\s+([0-9,]+)\s+jobs", text, re.I)
        end_reached = counts and int(counts.group(2).replace(",", "")) >= int(counts.group(3).replace(",", ""))
        tabs = page.locator(".tab.selected").inner_text()
        zero = bool(re.fullmatch(r"\s*Search Results\s*0\s*", tabs))
        hidden_last = any("hidden" in (control.get_attribute("class") or "").split()
                          or control.get_attribute("aria-disabled") == "true" for control in next_control.all())
        if end_reached or zero or hidden_last:
            return PaginationResult("verified_last_page", page.url, len(job_links(page)), method="controls")
    outcome = advance(page, [next_control,
        page.get_by_role("button", name=re.compile(r"^\s*Next\b", re.I)),
        page.get_by_role("link", name=re.compile(r"^\s*Next\b", re.I)),
    ], job_links, prefer_click=True, click_timeout=8000)
    require_search(page)
    if outcome:
        wait_search_ready(page)
        outcome.visible_job_count = len(job_links(page))
    return outcome


def read_job(page, url):
    import url_reader.engine as reader
    reader.navigate(page, url)
    reader.wait_for_content(page, DESCRIPTION)
    title = reader.first_text(page, ".profile-info h1, h1")
    company = re.sub(r"^at\s+", "", reader.first_text(page, ".profile-info .company-name, h2.company-name"), flags=re.I)
    description = reader.first_text(page, DESCRIPTION)
    if not title or not company or not description:
        raise ValueError("Instahyre title, company or description was missing; no empty listing was saved.")
    locations = reader.first_text(page, ".job-locations .location-span")
    experience = reader.first_text(page, ".job-locations .experience")
    skills = list(dict.fromkeys(text.strip() for text in page.locator("#job-skills-description li").all_inner_texts()
                               if text.strip() and not re.fullmatch(r"\+[0-9]+", text.strip())))
    return annotate({"source": "instahyre", "job_id": posting_key(url)[1], "link": canonical_job_url(page.url),
                     "title": title, "company": company, "description": description,
                     "location_and_posting_info": "\n".join(filter(None, [locations, experience])),
                     "experience": experience, "skills": skills, "criteria": "\n".join(skills),
                     "extraction_method": "scoped_dom", "collected_at": datetime.now(timezone.utc).isoformat()})
