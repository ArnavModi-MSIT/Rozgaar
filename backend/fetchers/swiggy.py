"""Read the same public NextHire feed used by Swiggy careers."""
import base64
import json
import time
import requests
from backend.fetchers.http_client import post_json
from backend.fetchers.result import CollectionResult
from backend.fetchers.standard import strip_html

ENDPOINT = "https://swiggy.mynexthire.com/employer/careers/reqlist/get"
SESSION = requests.Session()
INDIA_CITIES = {'Vishakapatnam', 'Ooty', 'Mathura', 'Nizamabad', 'Thiruvallur', 'Trichy', 'Srinagar', 'Surat', 'Erode', 'Salem', 'Bharatpur', 'Karimnagar', 'Belgaum', 'Chittoor', 'Delhi', 'Ambala', 'Faridkot', 'Dharmapuri', 'Jaipur', 'Mumbai', 'Jamshedpur', 'Kota', 'Bengaluru', 'Pune', 'Bangalore', 'Krishnagiri', 'Ahmedabad', 'Bharuch', 'Sawai Madhopur', 'Baddi', 'Pondicherry', 'Sri Ganganagar', 'Kurnool', 'Nandyal', 'Hosur', 'Mumbai City', 'Chandigarh', 'Chennai', 'Patna', 'Sivakasi', 'Nagercoil', 'Raipur', 'Hyderabad', 'Kolkata', 'Vijayawada', 'Mangalore', 'Ongole', 'Nagpur', 'Coimbatore', 'Mysore', 'Udaipur', 'Alwar', 'Tirunelveli', 'Puri'}

def normalize_location(value):
    return value + ", India" if value in INDIA_CITIES else value


def job_url(req_id):
    context = {"pageType": "jd", "cvSource": "careers", "reqId": req_id,
               "requester": {"id": "", "code": "", "name": ""},
               "page": "careers", "bufilter": -1}
    tag = base64.b64encode(json.dumps(context, separators=(",", ":")).encode()).decode()
    return f"https://careers.swiggy.com/#/careers/apply?src=careers&p={tag}"


def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial", error="deadline reached before request")
    data = post_json(SESSION, ENDPOINT, json={"source": "careers", "code": "", "filterByBuId": -1})
    if not isinstance(data, dict) or not isinstance(data.get("reqDetailsBOList"), list):
        raise RuntimeError("Swiggy public careers response unavailable or invalid")
    jobs, seen, invalid, missing = [], set(), 0, 0
    for record in data["reqDetailsBOList"]:
        req_id = record.get("reqId")
        if not req_id or not record.get("reqTitle"):
            invalid += 1
            continue
        if str(req_id) in seen:
            continue
        seen.add(str(req_id))
        description = strip_html(record.get("jdDisplay", ""), max_chars=None)[:10000]
        if not description:
            missing += 1
        if record.get("expMin") is not None:
            description += f"\nSource minimum experience: {record['expMin']} years."
        jobs.append({"company": "swiggy", "source_id": str(req_id),
                     "title": record["reqTitle"],
                     "location": normalize_location(record.get("location") or record.get("locationAddress") or ""),
                     "description": description.strip(), "url": job_url(req_id)})
    errors = []
    if invalid:
        errors.append(f"{invalid} malformed listings")
    if missing:
        errors.append(f"{missing} descriptions unavailable")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
