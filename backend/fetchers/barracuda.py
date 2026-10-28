"""Barracuda's public careers-room feed, restricted to the supplied Bangalore scope."""
import re
import time
from urllib.parse import urljoin, urlsplit, parse_qs
import requests
from bs4 import BeautifulSoup
from .http_client import get_text, get_json
from .standard import strip_html
from .result import CollectionResult

BASE='https://www.barracuda.com'
SEARCH_URL=BASE+'/company/careers?location=Bangalore%252C%2520India'
LOCATION='Bangalore, India'


def _endpoint(html):
    soup=BeautifulSoup(html or '', 'html.parser')
    el=soup.select_one('[data-cmp-is="CareersRoom"] [data-cmp-hook-careers-room="cardsContainerFeatured"][data-panel-endpoint]')
    p=urlsplit(urljoin(BASE,el['data-panel-endpoint'])) if el else None
    if (not p or p.scheme!='https' or p.netloc!='www.barracuda.com'
            or not p.path.startswith('/content/barracuda-corp/us/en/company/careers/')
            or not p.path.endswith('.careers.json') or p.query or p.fragment):
        raise ValueError('Barracuda careers feed configuration unavailable')
    return BASE+p.path


def _job(row):
    sid=row.get('eId');title=row.get('title');url=row.get('detailLink')
    p=urlsplit(url) if isinstance(url,str) else None
    if (not isinstance(sid,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',sid)
            or not isinstance(title,str) or not title.strip() or row.get('postingType')!='External'
            or not p or p.scheme!='https' or p.netloc!='app.jobvite.com'
            or p.path!='/CompanyJobs/Job.aspx' or parse_qs(p.query).get('j')!=[sid]):
        raise ValueError('Barracuda public job identity/title/link unavailable')
    body=row.get('description')
    description=strip_html(body,max_chars=None) if isinstance(body,str) else ''
    # Only public job fields: do not copy feed customField or application metadata.
    return dict(company='barracuda',source_id=sid,title=title.strip(),location=LOCATION,
                url='https://app.jobvite.com/CompanyJobs/Job.aspx?j='+sid,description=description)


def collect(deadline=None):
    if deadline is not None and time.monotonic()>=deadline:raise RuntimeError('Barracuda: listing deadline reached')
    with requests.Session() as session:
        endpoint=_endpoint(get_text(session,SEARCH_URL))
        if deadline is not None and time.monotonic()>=deadline:raise RuntimeError('Barracuda: listing deadline reached')
        data=get_json(session,endpoint)
    if (not isinstance(data,dict) or not isinstance(data.get('jobs'),list)
            or not isinstance(data.get('locations'),list) or not isinstance(data.get('categories'),list)):
        raise RuntimeError('Barracuda careers feed schema unavailable')
    jobs,errors,seen=[],[],set()
    scoped=0
    for row in data['jobs']:
        if not isinstance(row,dict):errors.append('malformed feed row');continue
        if row.get('location')!=LOCATION:continue
        scoped+=1
        try:job=_job(row)
        except ValueError as exc:errors.append(str(exc));continue
        if job['source_id'] in seen:errors.append('duplicate job ID in feed');continue
        seen.add(job['source_id']);jobs.append(job)
        if not job['description']:errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs:raise RuntimeError('Barracuda: '+'; '.join(dict.fromkeys(errors)))
    result=CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(dict.fromkeys(errors))[:1200])
    result.source_counts=dict(feed_total=len(data['jobs']),scoped=scoped,unique=len(jobs),missing_descriptions=sum(not j['description'] for j in jobs))
    return result
