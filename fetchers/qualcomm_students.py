"""Qualcomm's public India Intern search and structured full descriptions."""
import json
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

import config
from . import eightfold
from .http_client import get_text
from .result import CollectionResult
from .standard import strip_html


def _description(job, deadline):
    if deadline is not None and time.monotonic() >= deadline:
        return ""
    with requests.Session() as session:
        session.headers['User-Agent'] = 'Mozilla/5.0'
        html = get_text(session, job['url']) or ''
    for script in BeautifulSoup(html, 'html.parser').select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.get_text())
        except ValueError:
            continue
        candidates = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and isinstance(data.get('@graph'), list):
            candidates += data['@graph']
        for item in candidates:
            if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                return strip_html(item.get('description') or '', max_chars=None)
    return ''


def collect(deadline=None):
    cfg = config.QUALCOMM_STUDENTS
    jobs, errors, seen, total = [], [], set(), None
    for start in range(0, 1000, eightfold.PAGE_SIZE):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append('listing deadline reached')
            break
        params = {key: cfg[key] for key in ('domain', 'location', 'sort_by',
                  'filter_include_remote', 'filter_include_relocation', 'filter_seniority')}
        params.update(query='', start=start)
        data = eightfold._get(cfg['host'], params)
        listing = data.get('data') if isinstance(data, dict) else None
        if not isinstance(listing, dict) or not isinstance(listing.get('positions'), list):
            if start == 0:
                raise RuntimeError('Qualcomm students: first listing unavailable')
            errors.append(f'listing offset {start} unavailable')
            break
        if total is None:
            total = listing.get('count')
            if not isinstance(total, int) or total < 0:
                raise RuntimeError('Qualcomm students: reported total unavailable')
        before = len(jobs)
        for row in listing['positions']:
            if not isinstance(row, dict) or not row.get('id') or not row.get('name'):
                errors.append('listing missing ID or title')
                continue
            identifier = str(row['id'])
            if identifier in seen:
                continue
            seen.add(identifier)
            job = eightfold._parse_position(row, cfg)
            # Use the verified first-party detail route, not arbitrary response links.
            job['url'] = f"https://{cfg['host']}/careers/job/{identifier}"
            job['description'] = ''
            jobs.append(job)
        if len(jobs) >= total:
            break
        if len(jobs) == before:
            errors.append('empty or repeated listing page')
            break
        time.sleep(0.3)
    else:
        errors.append('pagination safety limit reached')
    if total is None or len(jobs) != total:
        errors.append(f'received {len(jobs)} of {total} listings')
    if errors and not jobs:
        raise RuntimeError('Qualcomm students: ' + '; '.join(errors))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job, description in zip(jobs, pool.map(lambda job: _description(job, deadline), jobs)):
            job['description'] = description
            if not description:
                errors.append('description unavailable: ' + job['source_id'])
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(errors))
