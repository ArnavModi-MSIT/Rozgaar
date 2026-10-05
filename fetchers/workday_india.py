"""India-scoped Workday boards with live facets, full descriptions and partial status."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from .http_client import get_json, post_json
from .result import CollectionResult
from .standard import strip_html

def _facets(data):
    candidates = []
    def walk(items):
        for item in items:
            values=item.get("values") or []
            key=item.get("facetParameter", "")
            ids=[v.get("id") for v in values if v.get("id") and (v.get("descriptor", "").strip().lower()=="india" or re.match(r"IND[- ]",v.get("descriptor", "")) or re.search(r"\bIndia\b",v.get("descriptor", ""),re.I))]
            if ids and key: candidates.append((0 if "country" in key.lower() else 1,key,ids))
            walk([v for v in values if isinstance(v,dict) and "values" in v])
    walk(data.get("facets") or [])
    if not candidates: raise RuntimeError("India facet unavailable; cannot prove a scoped empty result")
    _,key,ids=sorted(candidates,key=lambda x:x[0])[0]
    return {key:ids}

def fetch(cfg,deadline=None):
    base=f"https://{cfg['tenant']}.{cfg['wd_server']}.myworkdayjobs.com"
    root=f"{base}/wday/cxs/{cfg['tenant']}/{cfg['site']}"
    headers={"Referer":f"{base}/en-US/{cfg['site']}"}
    jobs,errors,seen,total=[],[],set(),None
    with requests.Session() as session:
        def page(offset,facets): return post_json(session,root+"/jobs",json={"appliedFacets":facets,"limit":20,"offset":offset,"searchText":""},headers=headers)
        first=page(0,{})
        if not isinstance(first,dict) or not isinstance(first.get("jobPostings"),list): raise RuntimeError("Workday initial listing unavailable")
        facets=_facets(first)
        for offset in range(0,10000,20):
            if deadline is not None and time.monotonic()>=deadline:
                errors.append("listing deadline reached");break
            data=page(offset,facets)
            if not isinstance(data,dict) or not isinstance(data.get("jobPostings"),list):
                errors.append(f"listing offset {offset} failed");break
            if total is None: total=data.get("total")
            fresh=0
            for row in data["jobPostings"]:
                path=row.get("externalPath") or ""
                sid=str((row.get("bulletFields") or [path])[0])
                if not path or not row.get("title"):errors.append("invalid listing");continue
                if sid in seen:continue
                seen.add(sid);fresh+=1
                location=row.get("locationsText") or ""
                if not re.search(r"\bIndia\b",location,re.I):location=location+", India" if location else "India"
                jobs.append({"company":cfg["company"],"source_id":sid,"title":row["title"],"location":location,"url":f"{base}/en-US/{cfg['site']}{path}","description":"","_path":path})
            if total is not None and len(jobs)>=total:break
            if not fresh:errors.append("empty or repeated listing page");break
            time.sleep(0.3)
        else:errors.append("page limit reached")
    if total is None or len(jobs)!=total:errors.append(f"received {len(jobs)} of {total} listings")
    # Verify complete India pagination before selecting student titles.
    # Workday text search also matches descriptions (e.g. "internal"), so it
    # cannot be used as proof that a result is an internship.
    title_pattern = cfg.get("title_pattern")
    if title_pattern is not None:
        jobs = [job for job in jobs if title_pattern.search(job["title"])]
    def description(job):
        if deadline is not None and time.monotonic()>=deadline:return ""
        with requests.Session() as session:data=get_json(session,root+job["_path"],headers=headers)
        return strip_html(((data or {}).get("jobPostingInfo") or {}).get("jobDescription", ""),max_chars=None)[:10000]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job,desc in zip(jobs,pool.map(description,jobs)):
            job["description"]=desc
            job.pop("_path",None)
            if not desc:errors.append("description unavailable: "+job["source_id"])
    if errors and not jobs:raise RuntimeError("Workday India: "+"; ".join(errors[:5]))
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors[:5]))

def collect(configs,deadline=None):
    jobs,errors=[],[]
    for cfg in configs:
        try:
            result=fetch(cfg,deadline);jobs.extend(result)
            if result.status!="ok":errors.append(cfg["company"]+": "+result.error)
        except Exception as exc:errors.append(cfg["company"]+": "+str(exc))
    if errors and not jobs:raise RuntimeError("; ".join(errors))
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors))
