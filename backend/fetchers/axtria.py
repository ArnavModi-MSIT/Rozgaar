"""Axtria official India and FDE India cards with public SuccessFactors bodies."""
import re,time
from urllib.parse import urlsplit,parse_qs
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .standard import strip_html
from .result import CollectionResult
BASE='https://www.axtria.com/axtria-careers/'
SF='https://career10.successfactors.com/sfcareer/jobreqcareer'


def _list(html):
 soup=BeautifulSoup(html or '', 'html.parser');blocks=soup.select('#fde-career .career-bottom-tabs-manual-block')
 if not soup.select_one('#fde-career .career-bottom-tabs-manual'):raise ValueError('Axtria careers listing layout unavailable')
 jobs,errors,seen=[],[],set()
 for block in blocks:
  texts=block.select('.career-bottom-tabs-manual-left p');a=block.select_one('a.career-job-link[href]')
  if len(texts)<2 or not a:errors.append('Axtria malformed listing card');continue
  title,location=[x.get_text(' ',strip=True) for x in texts[:2]]
  # India tab also contains Hyderabad without a country suffix.
  india_tab=a.get('data-india-job')=='true'
  if not india_tab and not re.search(r'\bIndia\b',location,re.I):continue
  if not title or not location:errors.append('Axtria title/location unavailable');continue
  if not re.search(r'\bIndia\b',location,re.I):location+=', India'
  p=urlsplit(a['href']);q=parse_qs(p.query)
  if p.scheme=='https' and p.netloc=='career10.successfactors.com' and p.path in ['/sfcareer/jobreqcareer','/sfcareer/jobreqcareerpvt'] and q.get('company')==['axtriaindiP'] and re.fullmatch(r'\d+',q.get('jobId',[''])[0]):
   id=q['jobId'][0];url=SF+'?jobId='+id+'&company=axtriaindiP';sid='sf-'+id
   # Preserve only the view link actually published on Axtria's public page.
   # The share token is not guessed, obtained from an account or logged.
   if p.path.endswith('jobreqcareerpvt'):
    token=q.get('st',[''])[0]
    if not re.fullmatch(r'[A-Fa-f0-9]{20,80}',token):errors.append('Axtria published view link unavailable');continue
    url='https://career10.successfactors.com/sfcareer/jobreqcareerpvt?jobId='+id+'&company=axtriaindiP&st='+token
  elif p.scheme=='https' and p.netloc=='www.linkedin.com' and re.fullmatch(r'/jobs/view/\d+/?',p.path):
   id=p.path.strip('/').split('/')[-1];sid='linkedin-'+id;url='https://www.linkedin.com/jobs/view/'+id+'/'
  else:errors.append('Axtria unrecognized public job link');continue
  if sid in seen:continue
  seen.add(sid);jobs.append(dict(company='axtria',source_id=sid,title=title,location=location,url=url,description=''))
 return jobs,errors


def _description(html,id):
 soup=BeautifulSoup(html or '', 'html.parser');title=soup.title;body=soup.select_one('.joqReqDescription .externalPosting')
 if not title or not re.search(r'\('+re.escape(id)+r'\)',title.get_text(' ',strip=True)) or not body:
  raise ValueError('Axtria public detail identity or description unavailable')
 for e in body.select('script,style,form,button'):e.decompose()
 text=strip_html(str(body),max_chars=None)
 if not text:raise ValueError('Axtria full description unavailable')
 return text


def collect(deadline=None):
 if deadline is not None and time.monotonic()>=deadline:raise RuntimeError('Axtria listing deadline reached')
 with requests.Session() as session:jobs,errors=_list(get_text(session,BASE))
 def enrich(job):
  if job['source_id'].startswith('linkedin-'):return '', 'LinkedIn-only description unavailable: '+job['source_id']
  if deadline is not None and time.monotonic()>=deadline:return '', 'detail deadline reached'
  try:
   with requests.Session() as session:html=get_text(session,job['url'])
   return _description(html,job['source_id'].split('-',1)[1]),''
  except ValueError:return '', 'public description unavailable: '+job['source_id']
 with ThreadPoolExecutor(max_workers=3) as pool:
  for job,(description,error) in zip(jobs,pool.map(enrich,jobs)):
   job['description']=description
   if error:errors.append(error)
 if errors and not jobs:raise RuntimeError('Axtria: '+'; '.join(errors))
 result=CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(dict.fromkeys(errors))[:1200])
 result.source_counts=dict(unique=len(jobs),missing_descriptions=sum(not j['description'] for j in jobs))
 return result
