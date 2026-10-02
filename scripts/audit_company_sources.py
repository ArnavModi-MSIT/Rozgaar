"""Live source audit for the requested companies; never writes the job database."""
import argparse
import os
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import config
from core.collector import PLATFORMS
from core.location import parse_country
from fetchers import standard, workday, phenom, eightfold, oracle, smartrecruiters

DEDICATED = {"google":"google_careers", "amazon":"amazon", "mastercard":"mastercard_workday", "towerresearchcapital":"tower_research"}
SUMMARIES = {"google", "adobe", "expedia", "microsoft", "morganstanley", "qualcomm", "millennium", "netflix", "goldman_sachs"}

def resolve(key):
    if key in DEDICATED and DEDICATED[key] in dict(PLATFORMS):
        return DEDICATED[key],dict(PLATFORMS)[DEDICATED[key]]
    for group, fn in [("GREENHOUSE",standard.fetch_greenhouse),("LEVER",standard.fetch_lever),("ASHBY",standard.fetch_ashby)]:
        if key in getattr(config,group): return group.lower(), lambda deadline, fn=fn: fn(key)
    for group, fn in [("WORKDAY",workday.fetch_workday),("PHENOM",phenom.fetch_phenom),("EIGHTFOLD",eightfold.collect),("ORACLE",oracle.collect),("SMARTRECRUITERS",smartrecruiters.collect)]:
        entries=[x for x in getattr(config,group) if (x.get("company") or x.get("company_id"))==key]
        if entries:
            if group in {"WORKDAY","PHENOM"}: return group.lower(),lambda deadline, fn=fn, entry=entries[0]: fn(entry,deadline=deadline)
            return group.lower(),lambda deadline, fn=fn, entries=entries: fn(entries,deadline=deadline)
    platform=DEDICATED.get(key,key)
    callback=dict(PLATFORMS).get(platform)
    if callback: return platform,callback
    if hasattr(config,"WORKDAY_INDIA"):
        from fetchers import workday_india
        entries=[x for x in config.WORKDAY_INDIA if x["company"]==key]
        if entries:return "workday_india",lambda deadline:workday_india.fetch(entries[0],deadline)
    return None,None

def audit(row, seconds):
    result=dict(row)
    source,callback=resolve(row["key"])
    result["source"]=source
    result["checked_at"]=datetime.now(timezone.utc).isoformat()
    if not callback:return result|{"status":"unavailable" if row.get("availability_note") else "not_connected", "note":row.get("availability_note", "No configured collector")}
    started=time.monotonic()
    try:
        jobs=callback(started+seconds)
        india=[job for job in jobs if parse_country(job.get("location",""))=="India"]
        unknown=[job for job in jobs if parse_country(job.get("location",""))=="Unknown"]
        status=getattr(jobs,"status","returned")
        note=getattr(jobs,"error","") or ""
        if not hasattr(jobs,"status"):note="Fetcher has no completeness metadata; returned count does not prove full coverage."
        if time.monotonic()-started>=seconds:status="partial";note+=" Audit deadline reached."
        if not jobs and status=="returned":status="empty_unverified"
        result.update(status=status,total_returned=len(jobs),india_jobs=len(india),unknown_locations=len(unknown),india_descriptions=sum(bool(job.get("description")) for job in india),description_type=("none" if not any(job.get("description") for job in india) else "summary" if row["key"] in SUMMARIES else "description"),note=note)
    except Exception as exc:result.update(status="failed",note=f"{type(exc).__name__}: {exc}")
    result["elapsed_seconds"]=round(time.monotonic()-started,1)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--only",nargs="*")
    parser.add_argument("--seconds",type=int,default=240)
    parser.add_argument("--workers",type=int,default=4)
    args=parser.parse_args()
    if os.environ.get("JOB_INTEL_OFFLINE") == "1":raise SystemExit("Collection is disabled offline")
    rows=json.loads((ROOT/"COMPANY_SOURCES.json").read_text(encoding="utf-8"))
    if args.only:rows=[row for row in rows if row["key"] in args.only]
    output=ROOT/"COMPANY_SOURCE_AUDIT.json"
    previous=json.loads(output.read_text(encoding="utf-8")) if output.exists() else []
    results={row["key"]:row for row in previous}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending={pool.submit(audit,row,args.seconds):row for row in rows}
        for future in as_completed(pending):
            result=future.result();results[result["key"]]=result
            output.write_text(json.dumps(list(results.values()),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            print(result["name"],result["status"],result.get("india_jobs","-"),flush=True)
    return 0
if __name__=="__main__":raise SystemExit(main())
