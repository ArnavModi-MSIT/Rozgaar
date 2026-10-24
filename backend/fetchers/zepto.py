"""Zepto public Darwinbox careers listing, including descriptions."""
import time
import re
from html import unescape
import requests
from .http_client import get_text, post_json
from .standard import strip_html
from .result import CollectionResult
CAREERS="https://zepto.darwinbox.in/ms/candidatev2/main/careers/allJobs"
ENDPOINT="https://zepto.darwinbox.in/ms/candidateapi/job/alljobs"
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36","Referer":CAREERS,"Accept":"application/json, text/plain, */*"}

def normalize(row):
    sid=row.get("id");title=row.get("title") or row.get("designation_name")
    if not sid or not title:raise ValueError("Darwinbox job ID or title missing")
    location=row.get("locations") or ", ".join(row.get("officelocations_without_area") or []) or row.get("country", "")
    description=strip_html(unescape(row.get("jd", "")),max_chars=None)[:12000]
    return {"company":"zepto","source_id":str(sid),"title":title,"location":re.sub(r"\s*,\s*", ", ", " ".join(location.split())),"description":description,"url":CAREERS.rsplit('/',1)[0]+"/jobDetails/"+str(sid)}

def collect(deadline=None):
    jobs=[];seen=set();errors=[];total=None
    with requests.Session() as session:
        session.headers.update(HEADERS)
        if deadline is not None and time.monotonic()>=deadline:return CollectionResult(status="partial",error="deadline reached")
        if not get_text(session,CAREERS):raise RuntimeError("Zepto careers page unavailable")
        for page in range(1,501):
            if deadline is not None and time.monotonic()>=deadline:errors.append("deadline reached");break
            data=post_json(session,ENDPOINT,json={"page":page,"limit":20})
            if not isinstance(data,dict) or data.get("status")!="success" or not isinstance(data.get("data"),list):
                if not jobs:raise RuntimeError("Zepto public careers feed unavailable or invalid")
                errors.append(f"page {page} failed");break
            count=data.get("job_counts")
            if not isinstance(count,int) or count<0:
                errors.append("listing total unavailable");break
            if total is None:total=count
            elif total!=count:errors.append("listing total changed during collection")
            added=0
            for row in data["data"]:
                try:job=normalize(row)
                except (ValueError,TypeError,AttributeError):errors.append("malformed listing");continue
                if job["source_id"] in seen:continue
                seen.add(job["source_id"]);jobs.append(job);added+=1
                if not job["description"]:errors.append("description unavailable: "+job["source_id"])
            if len(jobs)>=total:break
            if not added:errors.append("empty or repeated listing page");break
        else:errors.append("page limit reached")
    if total is None or len(jobs)!=total:errors.append(f"received {len(jobs)} of {total} listings")
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors))
