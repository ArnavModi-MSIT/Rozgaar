"""LinkedIn employer only: public guest search, with explicit incomplete coverage."""
import time
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .result import CollectionResult
URL="https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
def collect(deadline=None):
    jobs=[];seen=set();errors=["Public search does not expose a reliable total; descriptions unavailable"]
    with requests.Session() as session:
        for start in range(0,250,25):
            if deadline is not None and time.monotonic()>=deadline:errors.append("deadline reached");break
            html=get_text(session,URL,params={"f_C":"1337","location":"India","start":start})
            if not html:errors.append("public search unavailable or rate limited");break
            soup=BeautifulSoup(html,"html.parser");cards=soup.select('.base-card')
            if not cards:break
            fresh=0
            for card in cards:
                employer=card.select_one('.base-search-card__subtitle')
                title=card.select_one('.base-search-card__title');link=card.select_one('a.base-card__full-link');loc=card.select_one('.job-search-card__location')
                sid=card.get('data-entity-urn','').rsplit(':',1)[-1]
                if not employer or employer.get_text(' ',strip=True).lower()!='linkedin':continue
                if not sid or sid in seen or not title or not link:continue
                seen.add(sid);fresh+=1
                jobs.append({"company":"linkedin_company","source_id":sid,"title":title.get_text(' ',strip=True),"location":loc.get_text(' ',strip=True) if loc else '',"url":link['href'].split('?')[0],"description":""})
            if not fresh:break
            time.sleep(1)
        else:errors.append("250 search offsets capped")
    if not jobs:raise RuntimeError('; '.join(errors))
    return CollectionResult(jobs,status="partial",error='; '.join(errors))
