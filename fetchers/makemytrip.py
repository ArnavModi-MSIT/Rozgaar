"""First-party MakeMyTrip careers API; no Darwinbox login is required."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlsplit
import requests
from core.experience import extract_min_experience
from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

ROOT = 'https://careers.makemytrip.com'
HEADERS = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept':'application/json', 'Referer':ROOT+'/prod/jobs',
}


def parse_detail(data, source_id):
    if not isinstance(data,dict) or data.get('status') != 1: return ''
    row = data.get('data') or {}
    # Detail responses omit job_id; the official apply URL identifies the job.
    apply = urlsplit(row.get('applyUrl') or '')
    if apply.hostname != 'gommt.darwinbox.in' or apply.path.rstrip('/').rsplit('/',1)[-1] != source_id:
        return ''
    desc = strip_html(row.get('job_decription') or '',max_chars=None)
    if not desc: return ''
    original_minimum = extract_min_experience(desc)
    unit = (row.get('unit_experience') or '').lower()
    if unit in {'years','year','months','month'}:
        try:
            lower = float(row['experience_from'])
            upper = float(row['experience_to'])
        except (KeyError,TypeError,ValueError): return desc
        if unit.startswith('month'): lower,upper = lower/12,upper/12
        if 0 <= lower <= upper <= 50:
            years = f'{lower:g}-{upper:g}' if upper != lower else f'{lower:g}'
            desc += '\n\nRequired Qualifications\n'+years+' years of professional experience required (career-site experience field).'
            if original_minimum is not None and original_minimum > lower:
                desc += f'\n{original_minimum:g} years of experience required (requirement stated in the job description).'
    return desc


def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline: raise RuntimeError('MakeMyTrip listing deadline reached')
    with requests.Session() as session:
        session.headers.update(HEADERS)
        data = get_json(session,ROOT+'/api/jobs')
    if not isinstance(data,dict) or not isinstance(data.get('allJobs'),list):
        raise RuntimeError('MakeMyTrip public listing unavailable')
    # The frontend receives the entire list in one response; Load More is local.
    jobs,seen,errors = [],set(),[]
    for row in data['allJobs']:
        sid = str(row.get('job_id') or '')
        if not sid or not row.get('job_title'):
            errors.append('listing lacks job identity/title'); continue
        if sid in seen: errors.append('duplicate listing ID: '+sid); continue
        seen.add(sid)
        if (row.get('location_country') or '').lower() != 'india': continue
        locations = row.get('location') or []
        if isinstance(locations,str): locations = [locations]
        slug = quote(re.sub(r'[/\s]','-',row['job_title'].lower()),safe='-')
        jobs.append(dict(company='makemytrip',source_id=sid,title=row['job_title'],location='; '.join(locations) or 'India',url=ROOT+'/prod/opportunity/'+sid+'/'+slug,description=''))
    def enrich(job):
        if deadline is not None and time.monotonic() >= deadline: return ''
        with requests.Session() as session:
            session.headers.update(HEADERS)
            data = get_json(session,ROOT+'/api/jobDetails',params={'jobId':job['source_id']})
        return parse_detail(data,job['source_id'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job,desc in zip(jobs,pool.map(enrich,jobs)):
            job['description'] = desc
            if not desc: errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
