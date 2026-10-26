"""Indeed public search/detail DOM reader; verification remains manual."""
import argparse
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from url_reader.identity import canonical_job_url, posting_key
from url_reader.quality import annotate
from url_reader.sources.wellfound import jobposting_data, description_text, location_text, salary_text

HOSTS = {'indeed.com', 'www.indeed.com', 'in.indeed.com'}
TRANSIENT_PARAMS = {'start', 'vjk', 'from', 'pp', 'xkcb', 'vjs'}
DEFAULT_SEARCH = 'https://in.indeed.com/jobs?' + urlencode([
    ('q',''), ('l','dwarka, delhi, delhi'), ('salaryType','₹2,40,000'),
    ('radius','25'), ('sc','0kf:attr(VDTG7);')])
RESULT_ITEM = '[data-jk], a[href*="/viewjob?"], a[href*="/rc/clk?"], a[href*="/pagead/clk?"]'
DESCRIPTION = '#jobDescriptionText, [data-testid="jobDescriptionText"]'


def search_url(value):
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == 'https' and parts.hostname in HOSTS and not parts.username and not parts.password
                 and parts.port in (None,443) and parts.path.rstrip('/') == '/jobs')
    except ValueError:
        valid = False
    if not valid:
        raise argparse.ArgumentTypeError('Use an https://in.indeed.com/jobs?... search URL.')
    pairs = [(k,v) for k,v in parse_qsl(parts.query,keep_blank_values=True) if k not in TRANSIENT_PARAMS]
    return urlunsplit(('https',parts.hostname.removeprefix('www.'),'/jobs',urlencode(pairs),''))


def job_links(page):
    values = page.locator(RESULT_ITEM).evaluate_all(r'''els => els.filter(el=>el.getClientRects().length && !el.closest('nav,footer')).flatMap(el=> {
        const key=el.getAttribute('data-jk');
        return [...(key && /^[0-9a-f]{16}$/i.test(key) ? [new URL('/viewjob?jk='+key,location.origin).href] : []),
                ...(el.href ? [el.href] : [])];
    })''')
    links = {}
    for value in values:
        key = posting_key(value)
        if key and key[0] == 'indeed':
            links.setdefault(key,canonical_job_url(value))
    return list(links.values())


def collect_links(page, limit, stop_event=None):
    import url_reader.engine as reader
    reader.check_cancel(stop_event)
    reader.check_access(page)
    return job_links(page)


def filtered_next_url(current, href):
    target = urlsplit(urljoin(current,href))
    search_url(urlunsplit(target))  # Require a supported HTTPS search route.
    if target.hostname.removeprefix('www.') != urlsplit(current).hostname.removeprefix('www.'):
        raise ValueError('Indeed pagination changed the country website.')
    original = parse_qsl(urlsplit(search_url(current)).query,keep_blank_values=True)
    pairs = parse_qsl(target.query,keep_blank_values=True)
    existing = {key for key,_ in pairs}
    for key in {key for key,_ in original} & existing:
        if [v for k,v in pairs if k == key] != [v for k,v in original if k == key]:
            raise ValueError('Indeed pagination changed a search filter.')
    pairs.extend((k,v) for k,v in original if k not in existing)
    return urlunsplit(('https',target.hostname.removeprefix('www.'),'/jobs',urlencode(pairs),''))


def next_results(page):
    from url_reader.browser.pagination import advance
    return advance(page, [page.locator('a[data-testid="pagination-page-next"], button[data-testid="pagination-page-next"], a[aria-label="Next Page"], button[aria-label="Next Page"], a[aria-label="Next page"], button[aria-label="Next page"]')],
                   job_links, prepare_target=lambda href: filtered_next_url(page.url,href), results_timeout=15)


def read_job(page, url):
    import url_reader.engine as reader
    reader.navigate(page,url)
    reader.wait_for_content(page,DESCRIPTION+', h1')
    structured = {}
    description = ''
    for _ in range(20):
        reader.check_access(page)
        description = reader.first_text(page,DESCRIPTION)
        structured = jobposting_data(page.locator('script[type="application/ld+json"]').all_text_contents(),url)
        if description or structured.get('description'):
            break
        reader.interruptible_wait(page,500)
    title = reader.first_text(page,'h1.jobsearch-JobInfoHeader-title, [data-testid="jobsearch-JobInfoHeader-title"], h1') or structured.get('title','')
    company = reader.first_text(page,'[data-testid="inlineHeader-companyName"] a, [data-testid="inlineHeader-companyName"], [data-company-name="true"], .jobsearch-CompanyInfoContainer a')
    organization = structured.get('hiringOrganization')
    company = company or (organization.get('name','') if isinstance(organization,dict) else organization if isinstance(organization,str) else '')
    full = description_text(structured.get('description') or '')
    method = 'scoped_dom'
    if len(full) > len(description):
        description,method = full,'jobposting_jsonld'
    if not title or not company or not description:
        raise ValueError('Indeed title, company or description was missing; no empty listing was saved.')
    location = reader.first_text(page,'[data-testid="inlineHeader-companyLocation"], [data-testid="job-location"], #jobLocationText') or location_text(structured)
    salary = reader.first_text(page,'#salaryInfoAndJobType, [data-testid="salaryInfoAndJobType"]') or salary_text(structured.get('baseSalary'))
    return annotate({'source':'indeed','job_id':posting_key(url)[1],'link':canonical_job_url(url),
        'title':title,'company':company,'description':description,'location_and_posting_info':'\n'.join(filter(None,[location,salary])),
        'salary':salary,'skills':[],'criteria':'','date_posted':structured.get('datePosted',''),
        'valid_through':structured.get('validThrough',''),'employment_type':structured.get('employmentType',''),
        'extraction_method':method,'collected_at':datetime.now(timezone.utc).isoformat()})
