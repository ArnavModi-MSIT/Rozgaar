"""HSBC's anonymous Eightfold apply-v2 India search and full job bodies."""
import re
import time
from urllib.parse import urlsplit

import requests

from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

BASE = 'https://portal.careers.hsbc.com'
ENDPOINT = BASE + '/api/apply/v2/jobs'
PAGE_SIZE = 10
MAX_PAGES = 500


def _page(data):
    if not isinstance(data, dict) or data.get('domain') != 'hsbc.com' or not isinstance(data.get('positions'), list):
        raise ValueError('HSBC search schema/domain unavailable')
    count = data.get('count')
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError('HSBC search total unavailable')
    if data.get('fuzzyResultsReturned'):
        raise ValueError('HSBC returned fuzzy results instead of the requested India search')
    return data['positions'], count


def _listing(row):
    if not isinstance(row, dict) or row.get('isPrivate') is not False:
        raise ValueError('HSBC posting is not explicitly public')
    sid = str(row.get('id') or '')
    title = row.get('name')
    if not re.fullmatch(r'\d+', sid) or not isinstance(title, str) or not title.strip():
        raise ValueError('HSBC job identity/title unavailable')
    locations = row.get('locations') or [row.get('location')]
    if not isinstance(locations, list) or not locations or not all(isinstance(x, str) for x in locations):
        raise ValueError('HSBC locations unavailable')
    india = [x.strip() for x in locations if re.search(r'(?:^|,)\s*India\s*$', x, re.I)]
    if not india:
        raise ValueError('HSBC posting lacks India location evidence')
    url = row.get('canonicalPositionUrl')
    parts = urlsplit(url) if isinstance(url, str) else None
    if (not parts or parts.scheme != 'https' or parts.hostname != 'portal.careers.hsbc.com'
            or parts.username or parts.password or parts.port not in (None, 443)
            or parts.path != '/careers/job/'+sid or parts.query or parts.fragment):
        raise ValueError('HSBC detail URL does not match posting identity')
    return dict(company='hsbc',source_id=sid,title=title.strip(),location='; '.join(dict.fromkeys(india)),url=url,description='')


def _description(data, job):
    actual = _listing(data)
    if actual['source_id'] != job['source_id'] or actual['title'].casefold() != job['title'].casefold():
        raise ValueError('HSBC detail belongs to a different posting')
    body = data.get('job_description')
    text = strip_html(body, max_chars=None) if isinstance(body, str) else ''
    if not text:
        raise ValueError('HSBC full job description unavailable')
    return text


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    total, offset = None, 0
    with requests.Session() as session:
        for _ in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            try:
                rows, count = _page(get_json(session, ENDPOINT, params={
                    'domain':'hsbc.com','location':'India','start':offset,'num':PAGE_SIZE,'sort_by':'timestamp'}))
            except (ValueError, TypeError) as exc:
                errors.append(str(exc)); break
            if total is not None and total != count:
                errors.append('search total changed during collection')
            total = count
            fresh = 0
            for row in rows:
                try:
                    job = _listing(row)
                except (ValueError, TypeError) as exc:
                    errors.append(str(exc)); continue
                if job['source_id'] in seen:
                    continue
                seen.add(job['source_id']); fresh += 1; jobs.append(job)
            offset += len(rows)
            if offset >= total:
                break
            if not rows or not fresh:
                errors.append('empty or repeated page before reported total'); break
            time.sleep(0.1)
        else:
            errors.append('listing page limit reached')
        if total is not None and len(seen) != total:
            errors.append(f'received {len(seen)} unique India postings of {total}')
        if errors and not jobs:
            raise RuntimeError('HSBC: '+'; '.join(dict.fromkeys(errors))[:900])
        for job in jobs:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('detail deadline reached'); break
            try:
                data = get_json(session, ENDPOINT+'/'+job['source_id'],params={'domain':'hsbc.com'})
                job['description'] = _description(data, job)
            except (ValueError, TypeError) as exc:
                errors.append(job['source_id']+': '+str(exc))
            time.sleep(0.1)
    missing = sum(not job['description'] for job in jobs)
    if missing:
        errors.insert(0,f'{missing} full descriptions unavailable')
    result = CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(dict.fromkeys(errors))[:1200])
    result.source_counts = dict(reported=total,unique=len(seen),missing_descriptions=missing)
    return result
