"""Anonymous UBS BrassRing India search and complete detail sections."""
import json
import time
import requests
from bs4 import BeautifulSoup
from .http_client import get_text, post_json
from .result import CollectionResult
from .standard import strip_html

ROOT = 'https://jobs.ubs.com'
SEARCH_URL = ROOT+'/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=searchResults&SearchType=linkquery&LinkID=15231'


def parse_detail(data, sid):
    detail = ((data or {}).get('ServiceResponse') or {}).get('Jobdetails') or {}
    fields = detail.get('JobDetailQuestions') or []
    values = {q.get('VerityZone'):q.get('AnswerValue') for q in fields}
    if str(values.get('reqid')) != sid or values.get('formtext23','').strip().lower() != 'india' or detail.get('isActive') is not True:
        return ''
    if not values.get('jobdescription'): return ''
    return '\n\n'.join((q.get('QuestionName') or 'Your role')+'\n'+strip_html(q.get('AnswerValue') or '',max_chars=None)
        for q in fields if q.get('QuestionType') == 'textarea' and q.get('AnswerValue'))


def collect(deadline=None):
    jobs, seen, errors = [], set(), []
    def expired(): return deadline is not None and time.monotonic() >= deadline
    if expired(): raise RuntimeError('UBS listing deadline reached')
    with requests.Session() as session:
        html = get_text(session,SEARCH_URL)
        try:
            soup = BeautifulSoup(html or '', 'html.parser')
            pre = json.loads(soup.find(id='preLoadJSON')['value'])
            original = json.loads(pre['SmartSearchJSONValue'])
            token = soup.find('input',attrs={'name':'__RequestVerificationToken'})['value']
            cookie = soup.find(id='CookieValue')['value']
        except (TypeError,KeyError,ValueError): raise RuntimeError('UBS anonymous search configuration unavailable')
        session.headers.update({'RFT':token,'Content-Type':'application/json; charset=utf-8','X-Requested-With':'XMLHttpRequest','Referer':SEARCH_URL})
        query = dict(PartnerId=25008,SiteId=5012,Keyword='',Location='India',KeywordCustomSolrFields=original['KeywordCustomSolrFields'],LocationCustomSolrFields=original['LocationCustomSolrFields'],FacetFilterFields=None,TurnOffHttps=False,Latitude=0,Longitude=0,PowerSearchOptions={'PowerSearchOption':[]},encryptedsessionvalue=cookie)
        data = post_json(session,ROOT+'/TgNewUI/Search/Ajax/MatchedJobs',json=query)
        if not isinstance(data,dict) or not isinstance(data.get('JobsCount'),int): raise RuntimeError('UBS search unavailable')
        total = data['JobsCount']; page = 1
        while True:
            rows = (data.get('Jobs') or {}).get('Job',[])
            if not isinstance(rows,list): errors.append('invalid listing schema'); break
            before = len(seen)
            for row in rows:
                vals = {q.get('QuestionName'):q.get('Value') for q in row.get('Questions',[])}
                sid = str(vals.get('reqid') or '')
                if not sid or not vals.get('jobtitle') or sid in seen: errors.append('missing or duplicate job identity'); continue
                seen.add(sid)
                if vals.get('formtext23','').strip().lower() != 'india': errors.append('India search returned foreign location'); continue
                jobs.append(dict(company='ubs',source_id=sid,title=vals['jobtitle'],location='India',url=ROOT+'/TGnewUI/Search/home/HomeWithPreLoad?partnerid=25008&siteid=5012&PageType=JobDetails&jobid='+sid,description='',_site=vals.get('siteid')))
            if len(seen) >= total: break
            if len(seen) == before or expired(): errors.append('listing interrupted'); break
            page += 1
            paging = dict(partnerId=25008,siteId=5012,keyword='',location='India',keywordCustomSolrFields=query['KeywordCustomSolrFields'],locationCustomSolrFields=query['LocationCustomSolrFields'],linkId='',Latitude=0,Longitude=0,facetfilterfields={'Facet':[]},powersearchoptions={'PowerSearchOption':[]},SortType='LastUpdated',pageNumber=page,encryptedSessionValue=cookie)
            data = post_json(session,ROOT+'/TgNewUI/Search/Ajax/ProcessSortAndShowMoreJobs',json=paging)
            if not isinstance(data,dict) or data.get('JobsCount') != total: errors.append('pagination unavailable or total changed'); break
            if page > total+1: errors.append('pagination did not advance'); break
        if len(seen) != total: errors.append('unique job count differs from reported total')
        for job in jobs:
            site = job.pop('_site')
            if not expired():
                detail = post_json(session,ROOT+'/TgNewUI/Search/Ajax/JobDetails',json=dict(partnerId=25008,siteId=5012,jobid=job['source_id'],configMode='',jobSiteId=site,turnOffHttps=False))
                job['description'] = parse_detail(detail,job['source_id'])
                if job['description']:
                    fields = detail['ServiceResponse']['Jobdetails']['JobDetailQuestions']
                    city = next((q.get('AnswerValue') for q in fields if q.get('VerityZone') == 'formtext2'), '')
                    job['location'] = (strip_html(city,max_chars=None)+', India') if city else 'India'
            if not job['description']: errors.append('description unavailable: '+job['source_id'])
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
