"""MediaTek public tRPC jobs, retaining explicitly identified India offices."""
import json
import time
import requests
from .http_client import get_json
from .result import CollectionResult
from .standard import strip_html

INDIA_CITIES = {"noida", "bangalore", "bengaluru", "mumbai"}

def _job(row):
    location = ((row.get("properties") or {}).get("location") or {}).get("code", "").strip()
    if location.lower() not in INDIA_CITIES: return None
    sid = row.get("id")
    if not sid or not row.get("title"): return None
    return {"company":"mediatek", "source_id":sid, "title":row["title"], "location":location + ", India", "url":f"https://yourcareers.mediatek.com/en/jobs/{sid}", "description":strip_html(row.get("description") or "", max_chars=None)[:10000]}

def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    expected = None
    with requests.Session() as session:
        for page in range(1, 51):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("deadline reached"); break
            params = {"locales":"en_US", "page":page, "jobQueryInfo":{}, "filters":{"categorys":[],"workExperiences":[],"locations":[],"programs":[]}, "sortBy":"publishedDate", "order":"DESC", "limit":100}
            response = get_json(session, "https://yourcareers.mediatek.com/api/trpc/job.getJobs", params={"input":json.dumps({"json":params})})
            data = ((response or {}).get("result") or {}).get("data", {}).get("json", {})
            if not isinstance(data.get("jobs"), list) or not isinstance(data.get("pagination"), dict):
                if not seen: raise RuntimeError("MediaTek public job query unavailable")
                errors.append(f"page {page} unavailable"); break
            pagination = data["pagination"]
            expected = pagination.get("total_items")
            if pagination.get("current_page") != page:
                errors.append("wrong listing page returned"); break
            fresh = 0
            for row in data["jobs"]:
                sid = row.get("id")
                if sid in seen: continue
                seen.add(sid); fresh += 1
                job = _job(row)
                if job:
                    jobs.append(job)
                    if not job["description"]: errors.append("description unavailable: " + sid)
            if page >= pagination.get("total_pages", 0): break
            if not fresh: errors.append("repeated page"); break
        else: errors.append("page limit reached")
    if expected is None or len(seen) != expected: errors.append(f"read {len(seen)} of {expected} global listings")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
