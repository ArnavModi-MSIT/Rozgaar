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
    errors=[]
    seen=set()
    for row in data["data"]:
        if not isinstance(row,dict):
            errors.append("malformed listing")
            continue
        sid=row.get("id") or row.get("_id") or row.get("name")
        title=row.get("title") or row.get("job_title")
        if not isinstance(sid,(str,int)) or not str(sid).strip() or not isinstance(title,str) or not title.strip():
            errors.append("listing ID or title unavailable")
            continue
        sid=str(sid)
        if sid in seen:
            continue
        seen.add(sid)
        description=strip_html(row.get("description") or "",max_chars=None)
        if not description:
            errors.append("description unavailable: "+sid)
        # The current official frontend renders jobs as accordion cards keyed
        # by `name`; it does not publish individual detail URLs.
        jobs.append({"company":"zerodha","source_id":sid,"title":title.strip(),"location":row.get("location") or "","description":description,"url":row.get("url") or "https://careers.zerodha.com/"})
    if data["data"] and not jobs:
        raise RuntimeError("Zerodha job schema changed: no usable listing IDs/titles")
    if isinstance(data.get("count"),int) and data["count"]!=len(data["data"]):
        errors.append(f"received {len(data['data'])} of {data['count']} listings")
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors[:5]))
