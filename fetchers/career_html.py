"""Official Nutanix/MathWorks listings and MAQ's linked complete Atom feed.

Listing pagination is verified before India selection. Details use JobPosting
structured data; an inaccessible/changed page is a failure, never a valid zero.
"""
import json
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core.location import parse_country
from .http_client import get_text
from .result import CollectionResult
from .standard import strip_html
from .http_client import get_json
from .http_client import post_json


def structured_job(html):
    soup = BeautifulSoup(html, 'html.parser')
    def walk(value):
        if isinstance(value, dict):
            types = value.get('@type', [])
            if types == 'JobPosting' or isinstance(types, list) and 'JobPosting' in types:
                yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
    for node in soup.select('script[type="application/ld+json"]'):
        try:
            yield from walk(json.loads(node.get_text()))
        except (ValueError, TypeError):
            continue


def job_description(html):
    for job in structured_job(html):
        return strip_html(job.get('description') or '', max_chars=None)
    return ''


def parse_listing(html, company, base):
    soup = BeautifulSoup(html, 'html.parser')
    jobs = []
    if company == 'nutanix':
        for card in soup.select('.card-job[data-id]'):
            a = card.select_one('a.js-view-job')
            loc = card.select_one('.job-meta-location')
            if a and loc:
                jobs.append(dict(company=company, source_id=card['data-id'], title=a.get_text(' ', strip=True), location=loc.get_text(' ', strip=True), url=urljoin(base, a['href']), description=''))
        match = re.search(r'Displaying\s+\d+\s+to\s+\d+\s+of\s+(\d+)\s+matching jobs', soup.get_text(' ', strip=True))
        total = int(match[1]) if match else None
    else:
        for card in soup.select('td.search_result_desc'):
            a = card.select_one('.search_title a[href]')
            loc = card.select_one('.additional_field span')
            if a and loc:
                sid = re.search(r'/opportunities/(\d+)', a['href'])
                if sid:
                    jobs.append(dict(company=company, source_id=sid[1], title=a.get_text(' ', strip=True), location=loc.get_text(' ', strip=True).replace('IN-', 'India, '), url=urljoin(base, a['href']), description=''))
        count = soup.select_one('#max_link_bottom')
        total = int(count.get_text(strip=True)) if count and count.get_text(strip=True).isdigit() else None
    return jobs, total


def fetch(company, deadline=None):
    if company == 'mathworks': return collect_mathworks(deadline)
    base = 'https://careers.nutanix.com' if company == 'nutanix' else 'https://www.mathworks.com'
    path = '/en/jobs/' if company == 'nutanix' else '/company/jobs/opportunities/search?location%5B%5D=IN&display=max'
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for page in range(1, 101):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            url = base + path + (f'?page={page}' if company == 'nutanix' else '')
            html = get_text(session, url)
            if not html:
                errors.append(f'listing page {page} unavailable'); break
            rows, reported = parse_listing(html, company, base)
            if total is None: total = reported
            if reported is None:
                errors.append('listing total unavailable'); break
            fresh = [row for row in rows if row['source_id'] not in seen]
            jobs.extend(fresh); seen.update(row['source_id'] for row in fresh)
            if len(jobs) >= total: break
            if not fresh or company == 'mathworks':
                errors.append(f'incomplete listing: {len(jobs)} of {total}'); break
            time.sleep(.3)
        else: errors.append('page limit reached')
    if total is None or len(jobs) != total:
        errors.append(f'received {len(jobs)} of {total} listings')
    jobs = [job for job in jobs if parse_country(job['location']) == 'India']
    def enrich(job):
        if deadline is not None and time.monotonic() >= deadline: return ''
        with requests.Session() as session:
            html = get_text(session, job['url'])
        return job_description(html) if html else ''
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, desc in zip(jobs, pool.map(enrich, jobs)):
            job['description'] = desc
            if not desc: errors.append('description unavailable: ' + job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(errors[:5]))


def parse_maq_feed(xml):
    root = ET.fromstring(xml)
    ns = {'a':'http://www.w3.org/2005/Atom', 'j':'http://schemas.jobscore.com/atom'}
    if root.tag != '{http://www.w3.org/2005/Atom}feed':
        raise ValueError('JobScore Atom feed unavailable')
    jobs = []
    for entry in root.findall('a:entry', ns):
        location = next((c.get('term', '') for c in entry.findall('a:category', ns) if c.get('scheme', '').endswith('#location')), '')
        # JobScore supplies explicit country in the custom location field.
        country = entry.find('.//j:country', ns)
        if country is not None and country.text:
            location += ', ' + ('India' if country.text.upper() == 'IN' else country.text)
        if parse_country(location) != 'India': continue
        link = entry.find('a:link[@rel="alternate"]', ns)
        content = entry.find('a:content', ns)
        if link is None or content is None: raise ValueError('JobScore entry lacks URL or description')
        jobs.append(dict(company='maqsoftware', source_id=entry.findtext('a:id', '', ns).rsplit('/',1)[-1], title=entry.findtext('a:title','',ns), location=location, url=link.get('href'), description=strip_html(content.text or '', max_chars=None)))
    return jobs


def collect_maq(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        raise RuntimeError('MAQ listing deadline reached')
    with requests.Session() as session:
        xml = get_text(session, 'https://careers.jobscore.com/jobs/maqsoftware/feed.atom')
    if not xml: raise RuntimeError('MAQ feed unavailable')
    jobs = parse_maq_feed(xml)
    errors = [j['source_id'] for j in jobs if not j['description']]
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='Missing descriptions: '+','.join(errors) if errors else '')


def collect_micron(deadline=None):
    from .eightfold import _parse_position
    cfg = dict(company='micron', host='careers.micron.com', domain='micron.com')
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for start in range(0, 10000, 10):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            data = get_json(session, 'https://careers.micron.com/api/pcsx/search', params=dict(domain='micron.com', location='India', start=start, query='', sort_by='timestamp'))
            d = (data or {}).get('data') or {}
            positions = d.get('positions')
            if not isinstance(positions, list) or not isinstance(d.get('count'), int):
                errors.append(f'listing offset {start} unavailable'); break
            if total is None: total = d['count']
            fresh = 0
            for position in positions:
                job = _parse_position(position, cfg)
                if job['source_id'] in seen: continue
                seen.add(job['source_id']); jobs.append(job); fresh += 1
            if len(jobs) >= total: break
            if not fresh: errors.append('empty or repeated page'); break
            time.sleep(.3)
        else: errors.append('page limit reached')
    if total is None or len(jobs) != total: errors.append(f'received {len(jobs)} of {total} listings')
    jobs = [job for job in jobs if parse_country(job['location']) == 'India']
    def enrich(job):
        if deadline is not None and time.monotonic() >= deadline: return ''
        with requests.Session() as session: html = get_text(session, job['url'])
        return job_description(html) if html else ''
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, desc in zip(jobs, pool.map(enrich, jobs)):
            job['description'] = desc
            if not desc: errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(errors[:5]))


def sap_listing(html):
    """Read the public Next.js flight payload; never execute page scripts."""
    text = ''
    for node in BeautifulSoup(html, 'html.parser').find_all('script'):
        match = re.search(r'self\.__next_f\.push\((\[.*\])\)', node.get_text(), re.S)
        if match:
            try:
                value = json.loads(match[1])
                if len(value) > 1 and isinstance(value[1], str): text += value[1]
            except ValueError: continue
    match = re.search(r'"jobs":(?=\[)', text)
    counts = re.findall(r'"totalJobs":(\d+)', text)
    if not match or not counts: raise ValueError('SAP listing schema unavailable')
    return json.JSONDecoder().raw_decode(text[match.end():])[0], int(counts[-1])


def collect_sap(deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for page in range(1, 101):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            html = get_text(session, f'https://jobs.sap.com/en/jobs/?country=India&page={page}')
            if not html: errors.append('listing unavailable'); break
            try: rows, total = sap_listing(html)
            except ValueError as e: errors.append(str(e)); break
            fresh = 0
            for row in rows:
                if not row.get('id') or row['id'] in seen: continue
                seen.add(row['id']); fresh += 1
                jobs.append(dict(company='sap', source_id=row['id'], title=row['title'], location=row.get('locations',''), url=urljoin('https://jobs.sap.com',row['url']), description=''))
            if len(jobs) >= total: break
            if not fresh: errors.append('repeated listing page'); break
            time.sleep(.3)
    return _enrich_verified(jobs, total, errors, deadline)


def _enrich_verified(jobs, total, errors, deadline):
    if total is None or len(jobs) != total: errors.append(f'received {len(jobs)} of {total} listings')
    jobs = [job for job in jobs if parse_country(job['location']) == 'India']
    def enrich(job):
        if deadline is not None and time.monotonic() >= deadline: return ''
        with requests.Session() as session: html = get_text(session, job['url'])
        return job_description(html) if html else ''
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, desc in zip(jobs, pool.map(enrich,jobs)):
            job['description'] = desc
            if not desc: errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(errors[:5]))


def collect_lowes(deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for offset in range(0, 10000, 20):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            data = post_json(session, 'https://talent.lowes.com/widgets', json={
                'lang':'en_in', 'deviceType':'desktop', 'country':'in', 'pageName':'search-results',
                'size':20, 'from':offset, 'jobs':True, 'counts':True, 'refNum':'LOWEUS',
                'ddoKey':'refineSearch', 'selected_fields':{'country':['India']}, 'all_fields':['country','city'],
            })
            result = (data or {}).get('refineSearch') or {}
            rows = (result.get('data') or {}).get('jobs')
            if not isinstance(rows,list) or not isinstance(result.get('totalHits'),int):
                errors.append('listing unavailable'); break
            if total is None: total = result['totalHits']
            fresh = 0
            for row in rows:
                sid = row.get('jobId')
                if not sid or sid in seen: continue
                seen.add(sid); fresh += 1
                if row.get('country') != 'India': errors.append('unexpected country in India search')
                slug = re.sub(r'[^a-z0-9]+','-',row['title'].lower()).strip('-')
                jobs.append(dict(company='lowes', source_id=sid, title=row['title'], location=row.get('cityStateCountry') or f"{row.get('city','')}, {row.get('country','')}", url=f"https://talent.lowes.com/in/en/job/{row['jobSeqNo']}/{slug}", description=''))
            if len(jobs) >= total: break
            if not fresh: errors.append('repeated or empty page'); break
            time.sleep(.3)
    return _enrich_verified(jobs,total,errors,deadline)


def parse_mathworks_feed(xml):
    root = ET.fromstring(xml)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('MathWorks RSS feed unavailable')
    jobs = []
    for item in root.findall('./channel/item'):
        if item.findtext('location/country') != 'IN': continue
        sections = [('Job Summary','summary'), ('Responsibilities','responsibilities'), ('Required Qualifications','required_qualifications'), ('Qualifications','qualifications')]
        desc = '\n\n'.join(title+'\n'+strip_html(item.findtext(key) or '',max_chars=None) for title,key in sections if item.findtext(key))
        jobs.append(dict(company='mathworks', source_id=item.findtext('id'), title=item.findtext('title_raw') or item.findtext('title'), location=(item.findtext('location/city') or '')+', India', url=item.findtext('link'), description=desc))
    return jobs


def collect_mathworks(deadline=None):
    if deadline is not None and time.monotonic() >= deadline: raise RuntimeError('MathWorks deadline reached')
    with requests.Session() as session: xml = get_text(session,'https://www.mathworks.com/company/jobs/opportunities/rss.xml')
    if not xml: raise RuntimeError('MathWorks RSS unavailable')
    jobs = parse_mathworks_feed(xml)
    errors = [j['source_id'] for j in jobs if not j['description']]
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='Missing descriptions: '+','.join(errors) if errors else '')
