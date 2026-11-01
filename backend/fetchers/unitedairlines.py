"""United's public India search and identity-checked full Phenom descriptions."""
import json
import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from .http_client import get_text, post_json
from .result import CollectionResult
from .standard import strip_html

BASE = 'https://careers.united.com'
SEARCH_URL = BASE + '/us/en/c/digital-technology-jobs'
REFNUM = 'UAIUADUS'  # Published in the official page's phApp configuration.
PAGE_SIZE = 10
MAX_PAGES = 200


def _listing(row):
    if not isinstance(row, dict):
        raise ValueError('malformed listing')
    if row.get('refNum', REFNUM) != REFNUM or row.get('siteType') != 'external':
        raise ValueError('listing employer/visibility mismatch')
    if str(row.get('country', '')).strip().casefold() != 'india':
        raise ValueError('India filter not honored')
    sid, title = row.get('jobId'), row.get('title')
    if not isinstance(sid, str) or not re.fullmatch(r'[A-Z0-9]+', sid) or not isinstance(title, str) or not title.strip():
        raise ValueError('listing identity/title unavailable')
    if row.get('jobSeqNo') != REFNUM + sid + 'EXTERNALENUSTALEO':
        raise ValueError('listing employer/requisition mismatch')
    location = row.get('location')
    if not isinstance(location, str) or not location.strip():
        location = ', '.join(row[k] for k in ('city', 'state', 'country') if isinstance(row.get(k), str) and row[k])
    if not re.search(r'\bIndia\b', location, re.I):
        location += ', India'
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or 'job'
    # Never follow applyUrl: it points to a Taleo application, not the JD.
    return dict(company='unitedairlines', source_id=sid, title=title.strip(), location=location,
                url=f'{BASE}/us/en/job/{quote(sid)}/{slug}', description='')


def _description(html, job):
    for node in BeautifulSoup(html or '', 'html.parser').find_all('script'):
        script = node.get_text()
        match = re.search(r'phApp\.ddo\s*=\s*', script)
        if not match:
            continue
        try:
            data = json.JSONDecoder().raw_decode(script[match.end():])[0]
        except (TypeError, ValueError):
            continue
        detail = data.get('jobDetail') if isinstance(data, dict) else None
        detail_data = detail.get('data') if isinstance(detail, dict) else None
        row = detail_data.get('job') if isinstance(detail_data, dict) else None
        if not isinstance(row, dict) or detail.get('status') != 200:
            continue
        if (row.get('refNum') != REFNUM or row.get('jobId') != job['source_id']
                or str(row.get('title', '')).strip().casefold() != job['title'].casefold()
                or str(row.get('country', '')).strip().casefold() != 'india'
                or row.get('siteType') != 'external'):
            raise ValueError('detail identity/country mismatch')
        # External employer body and full qualifications; never internal HR
        # fields, recruiter metadata, AI summaries or search descriptionTeaser.
        body = row.get('externalDescription') or row.get('description')
        text = strip_html(body, max_chars=None) if isinstance(body, str) else ''
        qualification = row.get('qualifications')
        qualification = strip_html(qualification, max_chars=None) if isinstance(qualification, str) else ''
        if not text:
            raise ValueError('full description unavailable')
        if qualification and qualification not in text:
            text += '\n\n' + qualification
        return text
    raise ValueError('public job detail unavailable')


def fetch(cfg, deadline=None):
    jobs, errors, seen, total = [], [], set(), None
    with requests.Session() as session:
        session.headers['Referer'] = SEARCH_URL
        for page in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            payload = dict(lang='en_us', deviceType='desktop', country='us', pageName='category',
                           size=PAGE_SIZE, jobs=True, counts=True, pageId='page2', siteType='external',
                           keywords='', selected_fields={'country': ['India']}, refNum=REFNUM,
                           ddoKey='refineSearch', sort={'order': 'desc', 'field': 'postedDate'})
            payload['from'] = page * PAGE_SIZE
            response = post_json(session, BASE + '/widgets', json=payload)
            result = response.get('refineSearch') if isinstance(response, dict) else None
            data = result.get('data') if isinstance(result, dict) else None
            rows = data.get('jobs') if isinstance(data, dict) else None
            if (not isinstance(result, dict) or result.get('status') != 200 or not isinstance(rows, list)
                    or type(result.get('totalHits')) is not int or result['totalHits'] < 0):
                errors.append('listing/count unavailable'); break
            if total is not None and total != result['totalHits']:
                errors.append('search total changed')
            total = result['totalHits']
            fresh = 0
            for row in rows:
                try:
                    job = _listing(row)
                except ValueError as exc:
                    errors.append(str(exc)); continue
                if job['source_id'] in seen:
                    continue
                seen.add(job['source_id']); jobs.append(job); fresh += 1
            if len(jobs) >= total:
                break
            if not fresh:
                errors.append('empty/repeated listing page'); break
            time.sleep(.1)
        else:
            errors.append('listing page limit reached')
        if total is not None and len(jobs) != total:
            errors.append(f'received {len(jobs)} of {total} India listings')
        if errors and not jobs:
            raise RuntimeError('United Airlines: ' + '; '.join(dict.fromkeys(errors))[:1000])
        for job in jobs:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('detail deadline reached'); break
            try:
                job['description'] = _description(get_text(session, job['url']), job)
            except ValueError as exc:
                errors.append(job['source_id'] + ': ' + str(exc))
    missing = sum(not job['description'] for job in jobs)
    if missing:
        errors.insert(0, f'{missing} full descriptions unavailable')
    return CollectionResult(jobs, status='partial' if errors else 'ok',
                            error='; '.join(dict.fromkeys(errors))[:1200])
