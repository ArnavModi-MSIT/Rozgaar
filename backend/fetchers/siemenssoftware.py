"""Siemens Digital Industries Software India listings and DE Jobs detail bodies."""
import re
import time
import requests
from .http_client import get_json, post_json
from .result import CollectionResult
from .standard import strip_html

BASE = 'https://jobs.sw.siemens.com'
ENDPOINT = 'https://prod-search-api.jobsyn.org/api/v1/solr/search'
DETAIL = 'https://microsites.dejobs.org/jobs-sw-siemens-com/data/'
# Employer IDs published in this site's Nuxt configuration; not all Siemens units.
SITE_CONFIG = {'domain':'jobs.sw.siemens.com','buids':[38591,38526]}
PAGE_SIZE = 10
MAX_PAGES = 500


def _listing(row):
    if not isinstance(row,dict) or row.get('buid') not in SITE_CONFIG['buids']:
        raise ValueError('Siemens Software employer identity unavailable')
    if row.get('country_exact') != 'India':
        raise ValueError('Siemens Software posting lacks India country evidence')
    guid = str(row.get('guid') or '').upper()
    sid = str(row.get('reqid') or '')
    title = row.get('title_exact')
    slug = row.get('title_slug')
    if (not re.fullmatch(r'[A-F0-9]{32}',guid) or not re.fullmatch(r'[\w-]+',sid)
            or not isinstance(title,str) or not title.strip()
            or not isinstance(slug,str) or not re.fullmatch(r'[a-z0-9_-]+',slug)):
        raise ValueError('Siemens Software job identity/title unavailable')
    location = row.get('location_exact')
    if not isinstance(location,str) or not location.strip():
        raise ValueError('Siemens Software location unavailable')
    location_slug = re.sub(r'[^a-z0-9]+','-',location.lower()).strip('-')
    return dict(company='siemenssoftware',source_id=guid,title=title.strip(),location=re.sub(r'\bIND\b','India',location),
                url=f'{BASE}/{location_slug}/{slug}/{guid}/job/',description='',_guid=guid,_reqid=sid)


def _page(data,page):
    if not isinstance(data,dict) or not isinstance(data.get('jobs'),list) or not isinstance(data.get('featured_jobs'),list):
        raise ValueError('Siemens Software search schema unavailable')
    p=data.get('pagination') or {}
    total=p.get('total')
    if isinstance(total,bool) or not isinstance(total,int) or total<0 or p.get('page')!=page:
        raise ValueError('Siemens Software search total/page unavailable')
    return data['featured_jobs']+data['jobs'],total,p.get('has_more_pages')


def _description(data,job):
    actual=_listing(data)
    if (actual['_guid']!=job['_guid'] or actual['_reqid']!=job['_reqid']
            or actual['title'].casefold()!=job['title'].casefold() or 'deleted_at' in data):
        raise ValueError('Siemens Software detail identity changed or expired')
    body=data.get('html_description')
    text=strip_html(body,max_chars=None) if isinstance(body,str) else ''
    if not text:raise ValueError('Siemens Software full description unavailable')
    return text


def collect(deadline=None):
    jobs,errors,seen=[],[],set()
    total=None
    with requests.Session() as session:
        session.headers['X-Origin']='jobs.sw.siemens.com'
        for page in range(1,MAX_PAGES+1):
            if deadline is not None and time.monotonic()>=deadline:
                errors.append('listing deadline reached');break
            try:
                data=post_json(session,ENDPOINT,json={'data':{'location':'india','page':page,'offset':0,'num_items':PAGE_SIZE},'config':SITE_CONFIG})
                rows,count,more=_page(data,page)
            except (ValueError,TypeError) as exc:
                errors.append(str(exc));break
            if total is not None and total!=count:errors.append('search total changed during collection')
            total=count;fresh=0
            for row in rows:
                try:job=_listing(row)
                except (ValueError,TypeError) as exc:errors.append(str(exc));continue
                if job['source_id'] in seen:continue
                seen.add(job['source_id']);jobs.append(job);fresh+=1
            if more is False:break
            if not rows or not fresh:errors.append('empty or repeated page before search end');break
            time.sleep(.1)
        else:errors.append('listing page limit reached')
        if total is not None and len(jobs)!=total:errors.append(f'received {len(jobs)} unique India postings of {total}')
        if errors and not jobs:raise RuntimeError('Siemens Software: '+'; '.join(dict.fromkeys(errors))[:900])
        for job in jobs:
            if deadline is not None and time.monotonic()>=deadline:errors.append('detail deadline reached');break
            try:job['description']=_description(get_json(session,DETAIL+job['_guid']+'.json'),job)
            except (ValueError,TypeError) as exc:errors.append(job['source_id']+': '+str(exc))
            time.sleep(.1)
    missing=sum(not j['description'] for j in jobs)
    if missing:errors.insert(0,f'{missing} full descriptions unavailable')
    for job in jobs:
        job.pop('_guid',None)
        job.pop('_reqid',None)
    result=CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(dict.fromkeys(errors))[:1200])
    result.source_counts=dict(reported=total,unique=len(jobs),missing_descriptions=missing)
    return result
