"""Official HRT WordPress careers listing, filtered to confirmed India locations."""
import json
import time
import requests
from bs4 import BeautifulSoup
from .http_client import get_text,post_json
from .result import CollectionResult
from core.location import parse_country
URL="https://www.hudsonrivertrading.com/careers/"
def collect(deadline=None):
    if deadline is not None and time.monotonic()>=deadline:return CollectionResult(status="partial",error="deadline reached")
    with requests.Session() as session:
        # Distinguish HTTP rejection from a real careers-page layout change.
        responses=[]
        session.hooks['response'].append(lambda response,*args,**kwargs: responses.append(response.status_code))
        html=get_text(session,URL)
        if not html:
            status=f"HTTP {responses[-1]}" if responses else "network request failed"
            raise RuntimeError(f"HRT careers page unavailable ({status}); no listings fetched")
        soup=BeautifulSoup(html,"html.parser")
        if soup.title and 'just a moment' in soup.title.get_text().lower():
            raise RuntimeError("HRT careers page returned an access challenge; no listings fetched")
        wrapper=soup.select_one('.hrt-card-wrapper[data-filters-settings]')
        if not wrapper:raise RuntimeError("HRT careers settings unavailable")
        data=post_json(session,"https://www.hudsonrivertrading.com/wp-admin/admin-ajax.php",data={"action":"get_hrt_jobs_handler","setting":wrapper['data-filters-settings'],"data":"","queryparams":""})
        if not isinstance(data,list):raise RuntimeError("HRT careers response unavailable")
        jobs=[]
        for row in data:
            card=BeautifulSoup(row.get("content", ""),"html.parser")
            link=card.select_one('.hrt-card-title')
            loc=card.select_one('.hrt-card-meta-desktop .hrt-card-info-list')
            location=loc.get_text(', ',strip=True) if loc else ""
            if parse_country(location)!="India":continue
            if not link or not link.get('href'):raise RuntimeError("HRT card schema changed")
            jobs.append({"company":"hrt","source_id":str(row['ID']),"title":link.get_text(' ',strip=True),"location":location,"url":link['href'],"description":row.get('description', '')})
    return CollectionResult(jobs,status="partial" if jobs else "ok",error="Descriptions are listing summaries" if jobs else "")
