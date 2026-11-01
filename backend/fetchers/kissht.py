"""Kissht Workline public vacancies; no candidate/application operations."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from .http_client import get_json, get_text, post_json
from .result import CollectionResult

BASE = 'https://app1596.workline.hr'
SEARCH_URL = BASE + '/Cportal/GeneralOpening.aspx'

def _listing(row):
    if row.get('Company_Name') != 'Kissht' or row.get('Country_Name') != 'India':
        raise ValueError('employer/India mismatch')
    sid = str(row.get('ERFCode') or '')
    token, slug, title = row.get('TrackToken'), row.get('SearchKeyWord'), row.get('Position_Name')
    if (not sid.isdigit() or not isinstance(token,str) or not re.fullmatch(r'[0-9a-fA-F-]{36}',token)
        or not isinstance(slug,str) or not slug or not isinstance(title,str) or not title.strip()):
        raise ValueError('job identity/title unavailable')
    title += (' - ' + row['ExternalJobName']) if row.get('ExternalJobName') else ''
    location = ', '.join(dict.fromkeys(str(row[k]).strip() for k in ('LOCATIONNAME','State_Name','Country_Name') if row.get(k)))
    return dict(company='kissht',source_id=sid,title=title.strip(),location=location,
                url=BASE+'/CandidatePortal/'+token+'/'+quote(slug,safe=''),description='')

def _description(html, job):
    soup=BeautifulSoup(html or '', 'html.parser')
    title=soup.select_one('.jobs-content h6')
    if not title or title.get_text(' ',strip=True)!=job['title']:
        raise ValueError('detail title mismatch/unavailable')
    meta=soup.select_one('.jobs-meta')
    if not meta or not re.search(r'\bKissht\b',meta.get_text(' ',strip=True)):
        raise ValueError('detail employer unavailable')
    blocks=soup.select('.description-info, .responsibilities')
    if not blocks:raise ValueError('description layout unavailable')
    content=[]
    for block in blocks:
        for e in block.select('h4,script,style,form,button'):e.decompose()
        text=block.get_text('\n',strip=True)
        if text:content.append(text)
    body='\n\n'.join(content)
    short=len(body)<100
    for li in soup.select('.job-short-info li'):
        text=li.get_text(' ',strip=True)
        if text.startswith(('Qualifications:', 'Experience:')):content.append(text)
    return '\n\n'.join(content),short

def fetch(cfg,deadline=None):
    if deadline is not None and time.monotonic()>=deadline:raise RuntimeError('Kissht listing deadline reached')
    with requests.Session() as session:
        html=get_text(session,SEARCH_URL)
        if not html or 'Kissht' not in BeautifulSoup(html,'html.parser').get_text():raise RuntimeError('Kissht portal identity unavailable')
        data=post_json(session,BASE+'/CPortal/generalopening.aspx/GetCurrentopening',json={'JDFileName':'','OrgCode':'','KeyName':''})
    try:rows=json.loads(data['d']['obj1'])
    except (KeyError,TypeError,ValueError):raise RuntimeError('Kissht public list unavailable') from None
    if not isinstance(rows,list):raise RuntimeError('Kissht public list invalid')
    jobs,errors,seen=[],[],set()
    for row in rows:
        try:job=_listing(row)
        except (ValueError,TypeError,AttributeError) as exc:errors.append(str(exc));continue
        if job['source_id'] in seen:continue
        seen.add(job['source_id']);jobs.append(job)
    def detail(job):
        if deadline is not None and time.monotonic()>=deadline:return '',True
        try:
            with requests.Session() as session:return _description(get_text(session,job['url']),job)
        except (ValueError,requests.RequestException):return '',True
    with ThreadPoolExecutor(max_workers=3) as pool:
        for job,(text,short) in zip(jobs,pool.map(detail,jobs)):
            job['description']=text
            if short:errors.append('brief/missing source description: '+job['source_id'])
    if errors and not jobs:raise RuntimeError('Kissht: '+'; '.join(errors)[:800])
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors)[:1200])
