"""NetApp's first-party TalentBrew India search, following its actual next links."""
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .result import CollectionResult
from core.location import parse_country
ROOT='https://careers.netapp.com'
URL=ROOT+'/location/india-jobs/27600/1269750/2'
def _get(url):
 with requests.Session() as session:return get_text(session,url)
def parse_page(html):
 soup=BeautifulSoup(html or '', 'html.parser');root=soup.select_one('#search-results')
 if root is None:raise RuntimeError('NetApp listing unavailable')
 total=int(root['data-total-results']);page=int(root['data-current-page']);jobs=[]
 for link in soup.select('#search-results-list a[data-job-id]'):
  location=link.select_one('.job-location');title=link.select_one('h3');loc=location.get_text(' ',strip=True) if location else ''
  if parse_country(loc) != 'India':raise RuntimeError('NetApp India search returned foreign/unknown location')
  if not title:raise RuntimeError('NetApp listing title unavailable')
  jobs.append(dict(company='netapp',source_id=link['data-job-id'],title=title.get_text(' ',strip=True),location=loc,url=urljoin(ROOT,link['href']),description=''))
 next_link=next((a for a in soup.select('.pagination a[href]') if a.get_text(' ',strip=True).lower()=='next'),None)
 # TalentBrew may render a disabled next anchor pointing to the current page.
 next_url=urljoin(ROOT,next_link['href']) if next_link else None
 return jobs,total,page,next_url

def collect(deadline=None):
 jobs,seen,visited,errors=[],set(),set(),[];total=None;target=URL
 while target:
  if deadline is not None and time.monotonic()>=deadline:errors.append('listing deadline reached');break
  if target in visited or urlsplit(target).hostname != 'careers.netapp.com':errors.append('repeated/invalid pagination');break
  visited.add(target)
  try:batch,count,page,next_url=parse_page(_get(target))
  except (RuntimeError,ValueError,KeyError) as exc:
   if not jobs:raise RuntimeError(str(exc)) from exc
   errors.append(str(exc));break
  if total is None:total=count
  if total != count or page != len(visited):errors.append('total or page changed');break
  for job in batch:
   if job['source_id'] not in seen:seen.add(job['source_id']);jobs.append(job)
  if len(jobs)>=total:break
  if not batch:errors.append('empty listing page');break
  target=next_url
 if len(jobs)!=total:errors.append(f'received {len(jobs)} of {total} listings')
 def enrich(job):
  if deadline is not None and time.monotonic()>=deadline:return ''
  soup=BeautifulSoup(_get(job['url']) or '', 'html.parser');desc=soup.select_one('.ats-description')
  return desc.get_text('\n',strip=True) if desc else ''
 with ThreadPoolExecutor(max_workers=4) as pool:
  for job,desc in zip(jobs,pool.map(enrich,jobs)):
   job['description']=desc
   if not desc:errors.append('description unavailable: '+job['source_id'])
 return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
