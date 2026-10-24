"""Swiss Re's supplied India city search and complete first-party detail text."""
import re,time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .result import CollectionResult
ROOT='https://www.swissre.com'
URL=ROOT+'/careers/jobSearch.html?searchterm=&country=IN&city=Bangalore&city=Hyderabad&city=Mumbai'
def _get(url):
 with requests.Session() as session: return get_text(session,url)
def _card_location(location,anchor):
 # Accessible link text explicitly lists each city/state/country, while the
 # visual location repeats mobile/desktop text and adds '+ 1 more' controls.
 pairs=re.findall(r'([^(),]+?)\s*\(\s*[A-Z0-9-]+\s*,\s*([A-Z]{2})\s*\)',anchor.get_text(' ',strip=True))
 if pairs:
  labels=[]
  for city,country in pairs:
   if country=='IN':labels.append(re.sub(r'^and\s+','',re.sub(r'\s+',' ',city).strip(' ,.'))+', India')
  if labels:return '; '.join(dict.fromkeys(labels))
  raise RuntimeError('Swiss Re search returned foreign or unknown location')
 primary=location.select_one('.is-hidden-mobile-portrait, .is-visible-mobile-portrait')
 if primary:
  primary=BeautifulSoup(str(primary),'html.parser')
  for control in primary.select('[aria-hidden="true"]'):control.decompose()
  loc=primary.get_text(' ',strip=True)
 else:loc=location.get_text(' ',strip=True).removeprefix('Location').strip()
 if not re.search(r',\s*IN$',loc):raise RuntimeError('Swiss Re search returned foreign or unknown location')
 return re.sub(r',\s*IN$',', India',loc)

def parse_listing(html):
 soup=BeautifulSoup(html or '', 'html.parser')
 count=re.search(r'Showing\s+\d+\s+of\s+(\d+)',soup.get_text(' ',strip=True))
 if not count: raise RuntimeError('Swiss Re reported count unavailable')
 jobs=[]
 for card in soup.select('.JobTeaser'):
  anchor=card.select_one('a.JobTeaser--link[href]'); title=card.select_one('.JobTeaser--title'); location=card.select_one('.JobTeaser--location')
  if not anchor or not title or not location: raise RuntimeError('Swiss Re job card incomplete')
  loc=_card_location(location,anchor)
  target=urljoin(ROOT,anchor['href']); sid=target.rstrip('/').rsplit('/',1)[-1]
  if not target.startswith(ROOT+'/careers/job/') or not sid.isdigit(): raise RuntimeError('Swiss Re invalid job link')
  jobs.append(dict(company='swissre',source_id=sid,title=title.get_text(' ',strip=True),location=loc,url=target,description=''))
 return jobs,int(count[1])
def parse_detail(html):
 soup=BeautifulSoup(html or '', 'html.parser')
 return '\n\n'.join(el.get_text('\n',strip=True) for el in soup.select('section.ArticleSection .richtext'))
def collect(deadline=None):
 if deadline is not None and time.monotonic()>=deadline: raise RuntimeError('Swiss Re listing deadline reached')
 jobs,total=parse_listing(_get(URL)); errors=[]
 if len(jobs)!=total or len({j['source_id'] for j in jobs})!=total: errors.append(f'received {len(jobs)} of {total} unique listings')
 def enrich(job):
  if deadline is not None and time.monotonic()>=deadline:return ''
  return parse_detail(_get(job['url']))
 with ThreadPoolExecutor(max_workers=4) as pool:
  for job,desc in zip(jobs,pool.map(enrich,jobs)):
   job['description']=desc
   if not desc: errors.append('description unavailable: '+job['source_id'])
 if errors and not jobs: raise RuntimeError('; '.join(errors))
 return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
