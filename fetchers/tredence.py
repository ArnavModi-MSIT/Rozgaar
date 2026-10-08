"""Public RippleHire search linked from Tredence's official careers page."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from .http_client import get_json, post_json
from .result import CollectionResult
from .standard import strip_html

ROOT = 'https://tredence.ripplehire.com/candidate/'
# Public career-site selector embedded in the official link, not a login token.
TOKEN = 'rzuz0vttMaz0VxxVzDiY'
INDIA_CITIES = {'bangalore','bengaluru','gurgaon','gurugram','pune','chennai','hyderabad','mumbai','noida','delhi'}


def india_location(text):
    parts = [part.strip() for part in (text or '').split(',')]
    if parts and all(part.lower() in INDIA_CITIES or part.lower() == 'india' for part in parts):
        return ', '.join(parts) + ('' if 'india' in [p.lower() for p in parts] else ', India')
    return ''


def collect(deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        for page in range(500):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            params = dict(token=TOKEN, source='CAREERSITE', page=page, search='*:*', pagesize=20)
            data = post_json(session, ROOT+'candidatejobsearch', data={'careerSiteUrlParams':json.dumps(params),'lang':'en'}, headers={'Accept':'application/json'})
            if not isinstance(data,dict) or not isinstance(data.get('jobVoList'),list) or not isinstance(data.get('totalJobCount'),int):
                errors.append('listing unavailable'); break
            if total is None: total = data['totalJobCount']
            fresh = 0
            for row in data['jobVoList']:
                sid = row.get('jobSeq')
                if not sid or sid in seen: continue
                seen.add(sid); fresh += 1
                location = india_location(row.get('locations'))
                if location:
                    jobs.append(dict(company='tredence', source_id=sid, title=row['jobTitle'], location=location, url=ROOT+f'?token={TOKEN}&source=CAREERSITE#detail/job/{sid}', description=''))
            if len(seen) >= total: break
            if not fresh: errors.append('empty or repeated page'); break
            time.sleep(.3)
        else: errors.append('page limit reached')
    if total is None or len(seen) != total: errors.append(f'received {len(seen)} of {total} listings')
    def enrich(job):
        if deadline is not None and time.monotonic() >= deadline: return ''
        with requests.Session() as session:
            data = get_json(session,ROOT+'candidatejobdetail',params=dict(token=TOKEN,jobSeq=job['source_id'],source='CAREERSITE',lang='en'),headers={'Accept':'application/json'})
        row = (data or {}).get('jobVO') or {}
        if str(row.get('jobSeq')) != job['source_id']: return ''
        return strip_html(row.get('jobDesc') or '',max_chars=None)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job,desc in zip(jobs,pool.map(enrich,jobs)):
            job['description'] = desc
            if not desc: errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
