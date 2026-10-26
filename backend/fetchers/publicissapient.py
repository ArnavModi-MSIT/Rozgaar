"""Publicis Sapient's public India search and full embedded job-detail sections."""
import json
import re
import time
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import requests

from .http_client import get_json, get_text
from .result import CollectionResult
from .standard import strip_html

BASE = 'https://careers.publicissapient.com'
SEARCH_URL = BASE+'/job-search?q=&country=India'
ENDPOINT = BASE+'/bin/ps-redesign/careersJobsearch'
PAGE_SIZE = 20
MAX_PAGES = 500


def _page(payload):
    response = payload.get('response') if isinstance(payload, dict) else None
    if not isinstance(response, dict) or not isinstance(response.get('docs'), list):
        raise ValueError('Publicis Sapient search response has no valid job list')
    total = response.get('numFound')
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError('Publicis Sapient search total unavailable')
    return response['docs'], total, response.get('start'), response.get('numFoundExact', True)


def _listing(row):
    if not isinstance(row, dict) or row.get('countryName') != 'India':
        raise ValueError('Publicis Sapient posting lacks India country evidence')
    sid = str(row.get('id') or row.get('jobId') or '')
    title = row.get('name')
    if not re.fullmatch(r'\d{4}-\d+(?:-\d+)?', sid) or not isinstance(title, str) or not title.strip():
        raise ValueError('Publicis Sapient job identity/title unavailable')
    parts = urlsplit(urljoin(BASE, row.get('jobDetailUrl') or ''))
    if (parts.scheme != 'https' or parts.hostname != 'careers.publicissapient.com'
            or parts.username or parts.password or parts.port not in (None, 443)
            or not parts.path.startswith('/job-details/'+sid+'-')):
        raise ValueError('Publicis Sapient detail URL does not match job identity')
    location = row.get('displayLocation') or ', '.join(str(row[key]) for key in ['city','region','countryName'] if row.get(key))
    if not re.search(r'\bIndia\b', location, re.I):
        location += ', India'
    return dict(company='publicissapient', source_id=sid, title=title.strip(), location=location,
                url=BASE+parts.path, description='')


def _description(html, sid):
    soup = BeautifulSoup(html, 'html.parser')
    component = soup.select_one('[data-cmp-is="careerjobdetailstemplate"][data-react-props]')
    if not component:
        raise ValueError('Publicis Sapient detail layout unavailable')
    props = json.loads(component['data-react-props'])
    if not isinstance(props, dict) or props.get('countryName') != 'India':
        raise ValueError('Publicis Sapient detail country unavailable or changed')
    # The canonical link is generic /job-details; use the page's visible Job ID.
    label = str(props.get('description') or '')
    match = re.search(r'\bJob ID:\s*([\d-]+)', label)
    # Search IDs append a location ID; the detail label uses the base requisition.
    requisition = '-'.join(sid.split('-')[:2])
    if not match or match.group(1) != requisition:
        raise ValueError('Publicis Sapient detail belongs to a different job')
    description = props.get('jobDescriptionSection') or {}
    body = description.get('body') if isinstance(description, dict) else None
    if not isinstance(body, str) or not strip_html(body, max_chars=None):
        raise ValueError('Publicis Sapient full description unavailable; snippet not substituted')
    sections = []
    for key in ['jobDescriptionSection','qualificationDescriptionSection','additionalInformationSection']:
        section = props.get(key)
        if not isinstance(section, dict):
            continue
        raw = section.get('body')
        text = strip_html(raw, max_chars=None) if isinstance(raw, str) else ''
        if text:
            sections.append(str(section.get('title') or '')+'\n'+text)
    return '\n\n'.join(sections).strip()


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    total, offset = None, 0
    with requests.Session() as session:
        for _ in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached')
                break
            try:
                rows, count, start, exact = _page(get_json(session, ENDPOINT, params={
                    'searchType':'/search','lang':'en','q':'','start':offset,'rows':PAGE_SIZE,'country':'India'}))
                if start != offset:
                    raise ValueError('Publicis Sapient returned the wrong pagination offset')
            except ValueError as exc:
                errors.append(str(exc))
                break
            if total is not None and total != count:
                errors.append('search total changed during collection')
            total = count
            if exact is not True:
                errors.append('search total is not exact')
            fresh = 0
            for row in rows:
                try:
                    job = _listing(row)
                except (ValueError, TypeError) as exc:
                    errors.append(str(exc))
                    continue
                if job['source_id'] in seen:
                    continue
                seen.add(job['source_id'])
                fresh += 1
                jobs.append(job)
            offset += len(rows)
            if offset >= count:
                break
            if not rows or not fresh:
                errors.append('empty or repeated page before reported total')
                break
            time.sleep(0.1)
        else:
            errors.append('listing page limit reached')
        if total is not None and len(seen) != total:
            errors.append(f'received {len(seen)} unique India postings of {total}')
        if errors and not jobs:
            raise RuntimeError('Publicis Sapient: '+'; '.join(dict.fromkeys(errors))[:900])
        for job in jobs:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('detail deadline reached')
                break
            try:
                html = get_text(session, job['url'])
                if html is None:
                    raise ValueError('detail request failed')
                job['description'] = _description(html, job['source_id'])
            except (ValueError, TypeError) as exc:
                errors.append(job['source_id']+': '+str(exc))
            time.sleep(0.1)
    missing = sum(not job['description'] for job in jobs)
    if missing:
        errors.insert(0, f'{missing} full descriptions unavailable')
    result = CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(dict.fromkeys(errors))[:1200])
    result.source_counts = dict(reported=total, unique=len(seen), missing_descriptions=missing)
    return result
