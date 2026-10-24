"""Official Automattic embedded vacancies; remote eligibility needs review."""
import json
import re
import time
import requests
from .http_client import get_text
from .standard import strip_html
from .result import CollectionResult

def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial",error="deadline reached")
    with requests.Session() as session: html=get_text(session,"https://automattic.com/jobs/")
    match=re.search(r"const ghJobsData\s*=\s*",html or "")
    if not match: raise RuntimeError("Automattic embedded jobs unavailable")
    rows,_=json.JSONDecoder().raw_decode(html[match.end():])
    if not isinstance(rows,list): raise RuntimeError("Invalid Automattic listing")
    jobs=[]
    for row in rows:
        if row.get("id") and row.get("title") and row.get("href"):
            jobs.append({"company":"automattic","source_id":str(row["id"]),"title":row["title"],"location":"Remote / location unspecified","url":row["href"],"description":strip_html(row.get("content",""),max_chars=None)[:10000]})
    return CollectionResult(jobs,status="partial",error="Individual geographic eligibility is unspecified; review each description")
