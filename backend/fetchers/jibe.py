"""Shared public Jibe India search with full descriptions and partial status."""
import time
import re
from urllib.parse import urlencode
from urllib.parse import quote
import requests
from backend.fetchers import icims
from backend.fetchers.result import CollectionResult
from backend.fetchers.standard import strip_html
from .http_client import get_json

def collect(company, domain, path, deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    for page in range(1, 501):
        if deadline is not None and time.monotonic() >= deadline:
            errors.append("deadline reached")
            break
        data = icims._fetch_page(domain, page, "/api/jobs", "country=India")
        if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
            if not jobs:
                raise RuntimeError("Public Jibe jobs response unavailable or invalid")
            errors.append(f"page {page} failed")
            break
        if isinstance(data.get("totalCount"), int):
            total = data["totalCount"]
        added = 0
        for entry in data["jobs"]:
            d = entry.get("data", entry)
            req_id = d.get("req_id") or d.get("slug")
            if not req_id or not d.get("title"):
                errors.append("malformed job record")
                continue
            if str(req_id) in seen:
                continue
            seen.add(str(req_id))
            description = strip_html(d.get("description", ""), max_chars=None)[:10000]
            if not description:
                errors.append(f"description unavailable: {req_id}")
            location = ", ".join(str(d[k]) for k in ("city", "state", "country") if d.get(k)) or d.get("location_name", "")
            jobs.append({"company": company, "source_id": str(req_id), "title": d["title"],
                         "location": location, "description": description,
                         "url": f"https://{domain}{path}/{d.get('slug') or req_id}"})
            added += 1
        if total is not None and len(jobs) >= total:
            break
        if not added:
            break
    else:
        errors.append("page limit reached")
    if total is None:
        errors.append("listing total unavailable")
    elif len(jobs) != total:
        errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))

def _job(row, cfg):
    data = row.get('data', row) if isinstance(row, dict) else None
    if not isinstance(data, dict):
        raise ValueError('malformed posting')
    if str(data.get('country', '')).strip().lower() != 'india':
        raise ValueError('posting lacks India country evidence')
    if cfg.get('client_code') and data.get('client_code') != cfg['client_code']:
        raise ValueError('posting employer mismatch')
    if cfg.get('brand') and data.get('tags2') != [cfg['brand']]:
        raise ValueError('posting brand mismatch')
    sid, slug, title = str(data.get('req_id') or ''), data.get('slug'), data.get('title')
    if (not sid or not isinstance(slug, str) or not re.fullmatch(r'[\w-]+', slug)
            or not isinstance(title, str) or not title.strip()):
        raise ValueError('posting identity/title unavailable')
    text = strip_html(data.get('description') or '', max_chars=None)
    # Jibe's description normally includes these sections. Preserve a section
    # separately if this employer supplies it only in its own field.
    for field in ('responsibilities', 'qualifications'):
        section = strip_html(data.get(field) or '', max_chars=None)
        if section and section not in text:
            text += '\n\n' + section
    location = ', '.join(dict.fromkeys(str(data[k]).strip() for k in ('city', 'state', 'country') if data.get(k)))
    return dict(company=cfg['company'], source_id=sid, title=title.strip(),
                location=location, url='https://' + cfg['host'] + cfg.get('job_path', '/jobs/') + quote(slug),
                description=text.strip())


def fetch(cfg, deadline=None):
    jobs, errors, seen, total = [], [], set(), None
    with requests.Session() as session:
        for page in range(1, 501):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            params = {'page': page, 'country': 'India'}
            if cfg.get('brand'):
                params['tags2'] = cfg['brand']
            data = get_json(session, 'https://' + cfg['host'] + '/api/jobs', params=params)
            if (not isinstance(data, dict) or not isinstance(data.get('jobs'), list)
                    or type(data.get('totalCount')) is not int or data['totalCount'] < 0):
                errors.append('listing/count unavailable'); break
            if total is not None and total != data['totalCount']:
                errors.append('listing total changed')
            total = data['totalCount']
            fresh = 0
            for row in data['jobs']:
                try:
                    job = _job(row, cfg)
                except (TypeError, ValueError) as exc:
                    errors.append(str(exc)); continue
                if job['source_id'] in seen:
                    continue
                seen.add(job['source_id']); jobs.append(job); fresh += 1
                if not job['description']:
                    errors.append('description unavailable: ' + job['source_id'])
            if len(jobs) >= total:
                break
            if not fresh:
                errors.append('empty/repeated page before search end'); break
            time.sleep(.1)
        else:
            errors.append('listing page limit reached')
    if total is not None and len(jobs) != total:
        errors.append(f'received {len(jobs)} of {total} listings')
    if errors and not jobs:
        raise RuntimeError('Jibe: ' + '; '.join(dict.fromkeys(errors))[:1000])
    return CollectionResult(jobs, status='partial' if errors else 'ok',
                            error='; '.join(dict.fromkeys(errors))[:1200])
