"""IBM public search: India catalogue and full indexed posting bodies."""
import re
import time
from urllib.parse import parse_qs, urlsplit

import requests
from .http_client import post_json
from .result import CollectionResult
from .standard import strip_html

ENDPOINT = 'https://www-api.ibm.com/search/api/v2'
SEARCH_URL = 'https://www.ibm.com/in-en/careers/search?field_keyword_05%5B0%5D=India'
PAGE_SIZE, MAX_PAGES = 100, 200
FIELDS = ['title', 'url', 'body', 'field_keyword_05', 'field_keyword_08',
          'field_keyword_17', 'field_keyword_18', 'field_keyword_19']


def _values(value):
    return value if isinstance(value, list) else [value] if value else []


def _page(data):
    hits = data.get('hits') if isinstance(data, dict) else None
    if not isinstance(hits, dict) or not isinstance(hits.get('hits'), list):
        raise ValueError('IBM search response has no hits list')
    total = hits.get('total')
    relation = total.get('relation', 'eq') if isinstance(total, dict) else 'eq'
    count = total.get('value') if isinstance(total, dict) else total
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError('IBM search response has no valid total')
    return hits['hits'], count, relation


def _record(hit):
    source = hit.get('_source') if isinstance(hit, dict) else None
    if not isinstance(source, dict):
        raise ValueError('posting has no source fields')
    if 'india' not in [str(v).strip().lower() for v in _values(source.get('field_keyword_05'))]:
        raise ValueError('posting lacks explicit India country')
    parts = urlsplit(source.get('url') or '')
    ids = parse_qs(parts.query).get('jobId') or []
    if (parts.scheme != 'https' or parts.hostname != 'careers.ibm.com' or parts.username
            or parts.password or parts.port not in (None, 443)
            or not parts.path.rstrip('/').endswith('/JobDetail')
            or len(ids) != 1 or not re.fullmatch(r'\d+', ids[0])):
        raise ValueError('posting has no valid IBM job identity')
    title = source.get('title')
    if not isinstance(title, str) or not title.strip():
        raise ValueError('posting title missing')
    locations = [str(v).strip() for v in _values(source.get('field_keyword_19')) if str(v).strip()]
    location = '; '.join(locations) or 'India'
    if not re.search(r'\bIndia\b', location, re.I):
        location += ', India'
    # description is a search snippet, never a full-text fallback.
    body = source.get('body')
    text = strip_html(body, max_chars=None) if isinstance(body, str) else ''
    return dict(company='ibm', source_id=ids[0], title=title.strip(), location=location,
                url=f'https://careers.ibm.com/careers/JobDetail?jobId={ids[0]}', description=text)


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    total, offset = None, 0
    with requests.Session() as session:
        session.headers.update({'Accept': 'application/json', 'Referer': SEARCH_URL})
        for _ in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('deadline reached')
                break
            payload = {'appId': 'careers', 'scopes': ['careers2'], 'size': PAGE_SIZE,
                       'from': offset, '_source': FIELDS,
                       # Default relevance ties drift between requests/replicas.
                       'sort': [{'_id': 'asc'}],
                       'query': {'bool': {'must': [{'term': {'field_keyword_05': 'India'}}]}}}
            data = post_json(session, ENDPOINT, json=payload)
            try:
                rows, count, relation = _page(data)
            except ValueError as exc:
                errors.append(str(exc))
                break
            if total is not None and count != total:
                errors.append(f'total changed from {total} to {count}')
            total = count
            if relation != 'eq':
                errors.append('search total is a lower bound')
            if data.get('timed_out') or (data.get('_shards') or {}).get('failed', 0):
                errors.append('search timed out or shards failed')
            fresh = 0
            for hit in rows:
                try:
                    job = _record(hit)
                except (ValueError, TypeError) as exc:
                    errors.append(str(exc))
                    continue
                if job['source_id'] in seen:
                    continue
                seen.add(job['source_id'])
                fresh += 1
                jobs.append(job)
                if not job['description']:
                    errors.append('full description unavailable: ' + job['source_id'])
            offset += len(rows)
            if relation == 'eq' and offset >= count:
                break
            if not rows or not fresh:
                errors.append('empty or repeated page before reported total')
                break
            time.sleep(0.2)
        else:
            errors.append('page limit reached')
    if total is not None and len(seen) != total:
        errors.append(f'received {len(seen)} unique postings of {total}')
    if errors and not jobs:
        raise RuntimeError('IBM careers: ' + '; '.join(dict.fromkeys(errors))[:700])
    return CollectionResult(jobs, status='partial' if errors else 'ok',
                            error='; '.join(dict.fromkeys(errors))[:1200])
