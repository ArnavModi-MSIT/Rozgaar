"""Exact PwC India experienced-careers page and Workday descriptions."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
import requests
from .http_client import get_text,get_json
from .result import CollectionResult
from .standard import strip_html
URL='https://www.pwc.in/careers/experienced-jobs.html'
ROOT='https://pwc.wd3.myworkdayjobs.com'

def listings(html):
    match=re.search(r'var\s+jsondata\s*=\s*',html or '')
    if not match: raise RuntimeError('PwC embedded listing unavailable')
    try: rows=json.JSONDecoder().raw_decode(html[match.end():])[0]
    except ValueError: raise RuntimeError('PwC listing JSON invalid')
    if not isinstance(rows,list): raise RuntimeError('PwC listing schema invalid')
    return rows

def detail(data,sid):
    info=(data or {}).get('jobPostingInfo') or {}
    if info.get('jobReqId') != sid or (info.get('country') or {}).get('descriptor') != 'India': return ''
    return strip_html(info.get('jobDescription') or '',max_chars=None)

def collect(deadline=None):
    jobs,seen,errors=[],set(),[]
    if deadline is not None and time.monotonic() >= deadline: raise RuntimeError("PwC listing deadline reached")
    with requests.Session() as session: rows=listings(get_text(session,URL))
    for row in rows:
        if row.get('iso') != 'IND': continue
        sid=row.get('jobreqid'); target=urlsplit(row.get('apply') or '')
        site=row.get('jobsite')
        prefix='/'+str(site)
        if not sid or not row.get('title') or target.hostname != 'pwc.wd3.myworkdayjobs.com' or not target.path.startswith(prefix+'/job/'):
            errors.append('invalid listing identity/link'); continue
        if sid in seen: continue
        seen.add(sid)
        path=target.path[len(prefix):].removesuffix('/apply')
        jobs.append(dict(company='pwc',source_id=sid,title=row['title'],location=(row.get('location') or '')+', India',url=ROOT+prefix+path,description='',_api=ROOT+'/wday/cxs/pwc/'+site+path))
    def enrich(job):
        if deadline is not None and time.monotonic() >= deadline: return ''
        with requests.Session() as session: data=get_json(session,job['_api'])
        return detail(data,job['source_id'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job,text in zip(jobs,pool.map(enrich,jobs)):
            job.pop('_api'); job['description']=text
            if not text: errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
