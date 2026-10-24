"""Naukri search/detail adapter; no private APIs or verification bypass."""
import argparse
import re
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from url_reader.quality import annotate
from url_reader.identity import canonical_job_url, posting_key

HOSTS = {"naukri.com", "www.naukri.com"}
DEFAULT_SEARCH = "https://www.naukri.com/analyst-internship-jobs?k=analyst%20internship&qproductJobSource=2&qinternshipFlag=true&naukriCampus=true&experience=0&nignbevent_src=jobsearchDeskGNB"
RESULT_ITEM = 'a[href*="/job-listings-"]'
DESCRIPTION = '[class*="dang-inner-html"], .job-desc, .jd-desc, .job-description, [itemprop="description"]'


def search_url(value):
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.password
            or parts.port not in (None, 443)
            or not re.fullmatch(r"/(?:[a-z0-9%+_-]+-)?jobs(?:-[a-z0-9%+_-]+)*/?", parts.path, re.I)):
        raise argparse.ArgumentTypeError("Use an https://www.naukri.com/...-jobs search URL.")
    path = re.sub(r"-[0-9]+$", "", parts.path.rstrip("/"))
    query = [(key, item) for key, item in parse_qsl(parts.query) if key not in {"page", "pageNo"}]
    return urlunsplit(("https", "www.naukri.com", path, urlencode(query), ""))


def job_links(page):
    values = page.locator(RESULT_ITEM).evaluate_all("els => els.map(el => el.href)")
    return list(dict.fromkeys(url for value in values if (url := canonical_job_url(value)) and posting_key(url)[0] == "naukri"))


def collect_links(page, limit, stop_event=None):
    import url_reader.engine as reader
    reader.check_cancel(stop_event)
    reader.check_access(page)
    return job_links(page)


def filtered_next_url(current, target):
    current_search = urlsplit(search_url(current))
    target_search = urlsplit(search_url(target))
    if current_search.path != target_search.path:
        raise ValueError("Naukri Next link belongs to a different search.")
    target_params = parse_qsl(urlsplit(target).query)
    replaced_keys = {key for key, _ in target_params}
    params = [(key, value) for key, value in parse_qsl(current_search.query)
              if key not in replaced_keys] + target_params
    parts = urlsplit(target)
    return urlunsplit(("https", "www.naukri.com", parts.path, urlencode(params), ""))


def next_results(page):
    import url_reader.engine as reader
    from url_reader.browser.pagination import advance, PaginationResult
    before = set(job_links(page))
    page.evaluate("window.scrollTo(0, document.scrollingElement.scrollHeight)")
    reader.interruptible_wait(page, 1000)
    reader.check_access(page)
    after = set(job_links(page))
    if after - before:
        return PaginationResult("advanced", page.url, len(after), method="scroll")
    match = re.search(r"-([0-9]+)/?$", urlsplit(page.url).path)
    current_number = int(match.group(1)) if match else 1
    def accept(target):
        number = re.search(r"-([0-9]+)/?$", urlsplit(target).path)
        return not number or int(number.group(1)) == current_number + 1
    return advance(page, [
        page.locator('a[rel="next"], a[aria-label="Next"], button[aria-label="Next"], a.fright'),
        page.get_by_role("link", name=re.compile(r"^Next\b", re.I)),
        page.get_by_role("button", name=re.compile(r"^Next\b", re.I)),
    ], job_links, accept_target=accept, prepare_target=lambda target: filtered_next_url(page.url, target),
       prefer_click=True)


def read_job(page, url):
    import url_reader.engine as reader
    reader.navigate(page, url)
    reader.wait_for_content(page, DESCRIPTION + ', h1')
    title = reader.first_text(page, 'h1, [class*="jd-header-title"], .jd-header-title')
    company = reader.first_text(page, '[class*="jd-header-comp-name"] a, [class*="jd-header-comp-name"], .jd-header .comp-name, .comp-name')
    description = reader.first_text(page, DESCRIPTION)
    # Public JobPosting JSON-LD can supply structured fields when the DOM differs.
    structured = jobposting_data(page, url)
    if not isinstance(structured, dict):
        structured = {}
    for _ in range(20):
        if description or structured.get("description"):
            break
        reader.interruptible_wait(page, 500)
        reader.check_access(page)
        description = reader.first_text(page, DESCRIPTION)
        structured = jobposting_data(page, url)
    company = company or reader.first_text(page, '[class*="jd-header-comp-name"] a, [class*="jd-header-comp-name"], .comp-name')
    title, company = title or structured.get("title", ""), company or structured.get("company", "")
    structured_description = structured.get("description", "")
    if len(structured_description) > len(description):
        description, method = structured_description, "jobposting_jsonld"
    else:
        method = "scoped_dom"
    if not title or not company or not description:
        raise ValueError("Naukri title, company or description was missing; no empty listing was saved.")
    location = reader.first_text(page, '[class*="locWdth"], [class*="location"], .loc')
    experience = reader.first_text(page, '[class*="expwdth"], [class*="experience"], .exp')
    salary = reader.first_text(page, '[class*="salary"], .sal')
    skills = list(dict.fromkeys(text.strip() for text in page.locator('[class*="key-skill"] a, .key-skill a, .key-skill span').all_inner_texts() if text.strip()))
    return annotate({"source": "naukri", "job_id": posting_key(url)[1], "link": canonical_job_url(url),
                     "title": title, "company": company, "description": description,
                     "location_and_posting_info": "\n".join(filter(None, [location, experience, salary])),
                     "experience": experience, "salary": salary, "skills": skills, "criteria": "\n".join(skills),
                     "date_posted": structured.get("date_posted", ""), "valid_through": structured.get("valid_through", ""),
                     "employment_type": structured.get("employment_type", ""), "extraction_method": method,
                     "collected_at": datetime.now(timezone.utc).isoformat()})


def jobposting_data(page, url):
    return page.evaluate("""expected => {
        const jobs=[];
        const visit = value => {
            if (!value || typeof value!=='object') return;
            if (Array.isArray(value)) { value.forEach(visit); return; }
            const types = Array.isArray(value['@type']) ? value['@type'] : [value['@type']];
            if(types.includes('JobPosting')) jobs.push(value);
            if(value['@graph']) visit(value['@graph']);
        };
        for(const node of document.querySelectorAll('script[type="application/ld+json"]')) {
            try { visit(JSON.parse(node.textContent)); } catch (_) {}
        }
        const matching = jobs.find(job => String(job.identifier?.value || job.identifier || '')===expected
            || String(job.url || '').split('?')[0].replace(/\\/$/,'')===location.href.split('?')[0].replace(/\\/$/,''));
        const single = jobs.length===1 && !jobs[0].identifier && !jobs[0].url ? jobs[0] : {};
        const job = matching || single;
        const html = new DOMParser().parseFromString(typeof job.description==='string' ? job.description : '','text/html');
        html.querySelectorAll('script,style').forEach(el=>el.remove());
        html.querySelectorAll('p,div,li,h1,h2,h3,br').forEach(el=>el.append(document.createTextNode('\\n')));
        const organization = job.hiringOrganization;
        return {title:typeof job.title==='string'?job.title:'',
            company:typeof organization?.name==='string'?organization.name:'',
            description:html.body.textContent.trim(),
            date_posted:typeof job.datePosted==='string'?job.datePosted:'',
            valid_through:typeof job.validThrough==='string'?job.validThrough:'',
            employment_type:typeof job.employmentType==='string'?job.employmentType:''};
    }""", posting_key(url)[1])
