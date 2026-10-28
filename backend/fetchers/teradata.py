"""Teradata's anonymous GR8 People India job search, including full HTML bodies."""
import re,time,unicodedata
import requests
from .http_client import post_json
from .standard import strip_html
from .result import CollectionResult
BASE='https://careers.teradata.com'
ENDPOINT=BASE+'/graphql'
PAGE_SIZE=20
QUERY='''query($first:Int,$after:String,$filters:JobPostingSearchFiltersInput){searchJobPostings(first:$first,after:$after,filters:$filters){results{nodes{key number title descriptionHTML primaryPlace{name} places{nodes{name}}}totalCount pageInfo{hasNextPage endCursor}}}}'''


def _page(data):
 if not isinstance(data,dict) or data.get('errors'):raise ValueError('Teradata GraphQL search failed')
 r=((data.get('data') or {}).get('searchJobPostings') or {}).get('results')
 if not isinstance(r,dict) or not isinstance(r.get('nodes'),list):raise ValueError('Teradata search schema unavailable')
 count=r.get('totalCount');info=r.get('pageInfo')
 if isinstance(count,bool) or not isinstance(count,int) or count<0 or not isinstance(info,dict) or not isinstance(info.get('hasNextPage'),bool):raise ValueError('Teradata count/pagination unavailable')
 return r['nodes'],count,info


def _job(row):
 if not isinstance(row,dict):raise ValueError('Teradata malformed job')
 sid=str(row.get('key') or '');title=row.get('title')
 if not re.fullmatch(r'\d+',sid) or not isinstance(title,str) or not title.strip():raise ValueError('Teradata job identity/title unavailable')
 nodes=(row.get('places') or {}).get('nodes') or []
 places=[r.get('name','') for r in nodes if isinstance(r,dict)]
 primary=(row.get('primaryPlace') or {}).get('name')
 if isinstance(primary,str):places.insert(0,primary)
 india=[p.strip() for p in places if isinstance(p,str) and re.search(r'(?:^|,)\s*India\s*$',p,re.I)]
 if not india:raise ValueError('Teradata posting lacks India location evidence')
 ascii_title=unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode()
 slug=re.sub(r'[^a-z0-9]+','-',ascii_title.lower()).strip('-') or 'job'
 body=row.get('descriptionHTML');description=strip_html(body,max_chars=None) if isinstance(body,str) else ''
 return dict(company='teradata',source_id=sid,title=title.strip(),location='; '.join(dict.fromkeys(india)),url=f'{BASE}/jobs/{sid}/{slug}',description=description)


def collect(deadline=None):
 jobs,errors,seen,cursors=[],[],set(),set();after=None;total=None
 with requests.Session() as session:
  session.headers['Apollo-Require-Preflight']='true'
  for _ in range(500):
   if deadline is not None and time.monotonic()>=deadline:errors.append('listing deadline reached');break
   try:
    rows,count,info=_page(post_json(session,ENDPOINT,json={'query':QUERY,'variables':{'first':PAGE_SIZE,'after':after,'filters':{'location':[{'address':'India'}]}}}))
   except (ValueError,TypeError) as exc:errors.append(str(exc));break
   if total is not None and total!=count:errors.append('search total changed during collection')
   total=count;fresh=0
   for row in rows:
    try:job=_job(row)
    except (ValueError,TypeError) as exc:errors.append(str(exc));continue
    if job['source_id'] in seen:continue
    seen.add(job['source_id']);jobs.append(job);fresh+=1
    if not job['description']:errors.append('description unavailable: '+job['source_id'])
   if not info['hasNextPage']:break
   cursor=info.get('endCursor')
   if not fresh or not isinstance(cursor,str) or not cursor or cursor in cursors:errors.append('empty/repeated page or invalid cursor');break
   cursors.add(cursor);after=cursor;time.sleep(.1)
  else:errors.append('listing page limit reached')
 if total is not None and len(jobs)!=total:errors.append(f'received {len(jobs)} unique India postings of {total}')
 if errors and not jobs:raise RuntimeError('Teradata: '+'; '.join(dict.fromkeys(errors))[:900])
 result=CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(dict.fromkeys(errors))[:1200]);result.source_counts=dict(reported=total,unique=len(jobs),missing_descriptions=sum(not j['description'] for j in jobs))
 return result
