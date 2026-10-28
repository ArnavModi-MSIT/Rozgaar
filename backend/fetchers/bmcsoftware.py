"""BMC Software's official India Avature search and full detail sections."""
import re,time
from urllib.parse import urljoin,urlsplit,parse_qs
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .standard import strip_html
from .result import CollectionResult
BASE='https://jobs.bmc.com'
SEARCH_URL=BASE+'/Careers/SearchJobs/?16484=%5B9406%5D&16484_format=5516&listFilterMode=1&jobRecordsPerPage=6'


def _url(url,detail=False):
 p=urlsplit(urljoin(BASE,url))
 if p.scheme!='https' or p.netloc!='jobs.bmc.com' or p.fragment:raise ValueError('BMC untrusted URL')
 if detail:
  if not re.fullmatch(r'/Careers/JobDetail/[^/]+/\d+',p.path) or p.query:raise ValueError('BMC detail URL invalid')
 else:
  q=parse_qs(p.query)
  if p.path!='/Careers/SearchJobs/' or q.get('16484')!=['[9406]'] or q.get('16484_format')!=['5516'] or q.get('listFilterMode')!=['1'] or q.get('jobRecordsPerPage')!=['6']:
   raise ValueError('BMC pagination changed India scope')
  if not re.fullmatch(r'\d+',q.get('jobOffset',['0'])[0]):raise ValueError('BMC pagination offset invalid')
 return p.geturl()


def _page(html):
 s=BeautifulSoup(html or '', 'html.parser');legend=s.select_one('.list-controls__text__legend')
 m=re.search(r'\bof\s+(\d+)\s+results?\b',legend.get_text(' ',strip=True),re.I) if legend else None
 if not m:raise ValueError('BMC search count/layout unavailable')
 jobs,errors=[],[]
 for card in s.select('article.article--result'):
  a=card.select_one('h3 a[href]');loc=card.select_one('.list-item-location')
  try:
   if not a or not a.get_text(strip=True) or not loc or not re.search(r'\bIndia\b',loc.get_text(),re.I):raise ValueError('BMC title/India location unavailable')
   url=_url(a['href'],True)
   jobs.append(dict(company='bmcsoftware',source_id=url.rsplit('/',1)[1],title=a.get_text(' ',strip=True),location=loc.get_text(' ',strip=True),url=url,description=''))
  except ValueError as exc:errors.append(str(exc))
 a=s.find('a',attrs={'aria-label':re.compile(r'^Go to Next Page',re.I)})
 return jobs,int(m.group(1)),_url(a['href']) if a else None,errors


def _description(html,job):
 s=BeautifulSoup(html or '', 'html.parser');fields={}
 for field in s.select('.detailData .article__content__view__field'):
  label=field.select_one('.article__content__view__field__label');value=field.select_one('.article__content__view__field__value')
  if label and value:fields[label.get_text(' ',strip=True)]=value.get_text(' ',strip=True)
 if fields.get('Job ID')!=job['source_id'] or fields.get('Country')!='India':raise ValueError('BMC detail identity/country mismatch')
 body=s.select_one('.detailDescription .article__content')
 if not body:raise ValueError('BMC full description unavailable')
 for el in body.select('form,button,script,style,.visibility--hidden'):el.decompose()
 text=strip_html(str(body),max_chars=None)
 if not text:raise ValueError('BMC full description empty')
 return text


def collect(deadline=None):
 jobs,errors,seen,visited=[],[],set(),set();url=SEARCH_URL;total=None
 with requests.Session() as session:
  for _ in range(500):
   if deadline is not None and time.monotonic()>=deadline:errors.append('listing deadline reached');break
   if url in visited:errors.append('repeated pagination link');break
   visited.add(url)
   try:rows,count,next_url,page_errors=_page(get_text(session,url))
   except ValueError as exc:errors.append(str(exc));break
   errors.extend(page_errors)
   if total is not None and total!=count:errors.append('search total changed during collection')
   total=count;fresh=0
   for job in rows:
    if job['source_id'] in seen:continue
    seen.add(job['source_id']);jobs.append(job);fresh+=1
   if not next_url:break
   if not fresh:errors.append('repeated or empty result page');break
   old=int(parse_qs(urlsplit(url).query).get('jobOffset',['0'])[0]);new=int(parse_qs(urlsplit(next_url).query).get('jobOffset',['0'])[0])
   if new<=old:errors.append('pagination offset did not advance');break
   url=next_url;time.sleep(.1)
  else:errors.append('listing page limit reached')
  if total is not None and len(jobs)!=total:errors.append(f'received {len(jobs)} unique India listings of {total}')
  if errors and not jobs:raise RuntimeError('BMC Software: '+'; '.join(dict.fromkeys(errors))[:900])
  for job in jobs:
   if deadline is not None and time.monotonic()>=deadline:errors.append('detail deadline reached');break
   try:job['description']=_description(get_text(session,job['url']),job)
   except ValueError as exc:errors.append(job['source_id']+': '+str(exc))
   time.sleep(.1)
 missing=sum(not j['description'] for j in jobs)
 if missing:errors.insert(0,f'{missing} full descriptions unavailable')
 result=CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(dict.fromkeys(errors))[:1200]);result.source_counts=dict(reported=total,unique=len(jobs),missing_descriptions=missing)
 return result
