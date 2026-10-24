"""Official Zerodha careers JSON feed."""
import time
import requests
from .http_client import get_json
from .standard import strip_html
from .result import CollectionResult

def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial",error="deadline reached")
    with requests.Session() as session:data=get_json(session,"https://careers.zerodha.com/api/jobs")
    if not isinstance(data,dict) or data.get("success") is not True or not isinstance(data.get("data"),list):
        raise RuntimeError("Zerodha careers feed unavailable")
    jobs=[]
    for row in data["data"]:
        sid=row.get("id") or row.get("_id")
        title=row.get("title") or row.get("job_title")
        if not sid or not title:raise RuntimeError("Zerodha job schema changed")
        jobs.append({"company":"zerodha","source_id":str(sid),"title":title,"location":row.get("location", ""),"description":strip_html(row.get("description",""),max_chars=None)[:10000],"url":row.get("url") or "https://careers.zerodha.com/"})
    return CollectionResult(jobs,status="partial" if jobs else "ok",error="Nonempty job schema requires live verification" if jobs else "")
