"""India-scoped Workday boards with live facets, full descriptions and partial status."""
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import requests
from .http_client import get_json, post_json
from .result import CollectionResult
from .standard import strip_html

def _facets(data, location_pattern=None):
    candidates = []
    def walk(items):
        for item in items:
            values=item.get("values") or []
            key=item.get("facetParameter", "")
            ids=[v.get("id") for v in values if v.get("id") and (v.get("descriptor", "").strip().lower()=="india" or re.match(r"IND[- ]",v.get("descriptor", "")) or re.search(r"\bIndia\b",v.get("descriptor", ""),re.I) or (location_pattern and re.search(location_pattern, v.get("descriptor", ""), re.I)))]
            if ids and key: candidates.append((0 if "country" in key.lower() else 1,key,ids))
            walk([v for v in values if isinstance(v,dict) and "values" in v])
    walk(data.get("facets") or [])
    if not candidates: raise RuntimeError("India facet unavailable; cannot prove a scoped empty result")
    _,key,ids=sorted(candidates,key=lambda x:x[0])[0]
    return {key:ids}

def fetch(cfg,deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial", error="deadline reached before listing")
    base=f"https://{cfg['tenant']}.{cfg['wd_server']}.myworkdayjobs.com"
    root=f"{base}/wday/cxs/{cfg['tenant']}/{cfg['site']}"
    headers={"Referer":f"{base}/en-US/{cfg['site']}"}
    jobs,errors,seen,total=[],[],set(),None
    with requests.Session() as session:
        def page(offset,facets): return post_json(session,root+"/jobs",json={"appliedFacets":facets,"limit":20,"offset":offset,"searchText":""},headers=headers)
        first=page(0,{})
        if not isinstance(first,dict) or not isinstance(first.get("jobPostings"),list): raise RuntimeError("Workday initial listing unavailable")
        global_scope = cfg.get("verify_global_country", False)
        facets={} if global_scope else _facets(first, cfg.get("india_facet_pattern"))
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
                bullets=row.get("bulletFields") or [path]
                index=cfg.get("id_bullet_index",0)
                sid=str(bullets[index] if index<len(bullets) else path)
                if not path or not row.get("title"):errors.append("invalid listing");continue
                if sid in seen:continue
                seen.add(sid);fresh+=1
                location=row.get("locationsText") or ""
                if not global_scope and not re.search(r"\bIndia\b",location,re.I):location=location+", India" if location else "India"
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
    local = threading.local()
    detail_sessions = []
    def description(job):
        if deadline is not None and time.monotonic()>=deadline:return {}
        # Reuse one connection pool per detail worker, never share a mutable
        # Session between workers. Large employer batches otherwise repeat a
        # TLS handshake for every vacancy.
        if not hasattr(local, "session"):
            local.session = requests.Session()
            detail_sessions.append(local.session)
        data=get_json(local.session,root+job["_path"],headers=headers)
        info = data.get("jobPostingInfo") if isinstance(data, dict) else None
        return info if isinstance(info, dict) else {}
    accepted=[]
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for job,info in zip(jobs,pool.map(description,jobs)):
                job.pop("_path",None)
                if global_scope or cfg.get("verify_detail_country"):
                    country_info = info.get("country")
                    country = country_info.get("descriptor") if isinstance(country_info, dict) else country_info if isinstance(country_info, str) else None
                    extra_india = [location for location in info.get("additionalLocations") or []
                                   if isinstance(location, str) and re.search(r"\bIndia\b", location, re.I)]
                    if country and country.lower() == "india":
                        location=info.get("location") or job["location"]
                        job["location"]=location+", India" if not re.search(r"\bIndia\b",location,re.I) else location
                    elif extra_india:
                        job["location"] = "; ".join(extra_india)
                    else:
                        if not country:errors.append("detail country unavailable: "+job["source_id"])
                        elif not global_scope:errors.append("non-India detail returned by scoped search: "+job["source_id"])
                        continue
                raw_desc = info.get("jobDescription", "")
                desc=strip_html(raw_desc if isinstance(raw_desc, str) else "",max_chars=None)
                job["description"]=desc;accepted.append(job)
                if not desc:errors.append("description unavailable: "+job["source_id"])
    finally:
        for session in detail_sessions:
            session.close()
    if deadline is not None and time.monotonic() >= deadline:
        errors.insert(0, "description deadline reached")
    jobs=accepted
    if errors and not jobs:raise RuntimeError("Workday India: "+"; ".join(errors[:5]))
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors[:5]))

def collect(configs,deadline=None):
    jobs,errors=[],[]
    # Each employer uses a different host; bounded overlap prevents a large
    # new batch from waiting behind every preceding company's descriptions.
    with ThreadPoolExecutor(max_workers=min(4,len(configs) or 1)) as pool:
        futures=[(cfg,pool.submit(fetch,cfg,deadline)) for cfg in configs]
        for cfg,future in futures:
            try:
                result=future.result();jobs.extend(result)
                if result.status!="ok":errors.append(cfg["company"]+": "+result.error)
            except Exception as exc:errors.append(cfg["company"]+": "+str(exc))
    if errors and not jobs:raise RuntimeError("; ".join(errors))
    return CollectionResult(jobs,status="partial" if errors else "ok",error="; ".join(errors))
