"""Official Swiggy jobs feed and identity-linked SmartRecruiters descriptions."""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urlunsplit
import requests
from backend.fetchers.http_client import get_json
from backend.fetchers.result import CollectionResult
from backend.fetchers.smartrecruiters import fetch_posting_description

ENDPOINT = "https://careers.swiggy.com/api/jobs.json"
SESSION = requests.Session()
INDIA_CITIES = {'Vishakapatnam', 'Ooty', 'Mathura', 'Nizamabad', 'Thiruvallur', 'Trichy', 'Srinagar', 'Surat', 'Erode', 'Salem', 'Bharatpur', 'Karimnagar', 'Belgaum', 'Chittoor', 'Delhi', 'Ambala', 'Faridkot', 'Dharmapuri', 'Jaipur', 'Mumbai', 'Jamshedpur', 'Kota', 'Bengaluru', 'Pune', 'Bangalore', 'Krishnagiri', 'Ahmedabad', 'Bharuch', 'Sawai Madhopur', 'Baddi', 'Pondicherry', 'Sri Ganganagar', 'Kurnool', 'Nandyal', 'Hosur', 'Mumbai City', 'Chandigarh', 'Chennai', 'Patna', 'Sivakasi', 'Nagercoil', 'Raipur', 'Hyderabad', 'Kolkata', 'Vijayawada', 'Mangalore', 'Ongole', 'Nagpur', 'Coimbatore', 'Mysore', 'Udaipur', 'Alwar', 'Tirunelveli', 'Puri'}

def normalize_location(value):
    return value + ", India" if value in INDIA_CITIES else value


def posting_identity(url):
    parsed = urlsplit(url)
    match = re.fullmatch(r'/SWIGGY/(\d+)(?:-[^/]*)?/?', parsed.path, re.I)
    if parsed.scheme != 'https' or parsed.netloc.lower() != 'jobs.smartrecruiters.com' or not match:
        raise ValueError('Unrecognized Swiggy posting URL')
    return match[1], urlunsplit(('https', parsed.netloc, parsed.path, '', ''))


def collect(deadline=None):
    if deadline is not None and time.monotonic() >= deadline:
        return CollectionResult(status="partial", error="deadline reached before request")
    data = get_json(SESSION, ENDPOINT)
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list) or type(data.get('total')) is not int or data['total'] < 0:
        raise RuntimeError("Swiggy public jobs feed unavailable or invalid")
    jobs, seen, invalid = [], set(), 0
    for record in data["jobs"]:
        try:
            req_id, url = posting_identity(record.get('u') or '')
            title = record.get('t')
            if not isinstance(title,str) or not title.strip():
                raise ValueError('Title missing')
        except (AttributeError, ValueError, TypeError):
            invalid += 1
            continue
        if req_id in seen:
            continue
        seen.add(req_id)
        jobs.append({"company": "swiggy", "source_id": req_id, "title":title.strip(),
                     "location": record.get('l') or normalize_location(record.get('c') or ''),
                     "description": '', "url":url})
    if data['jobs'] and not jobs:
        raise RuntimeError('Swiggy job schema changed: no usable postings')
    def description(job):
        if deadline is not None and time.monotonic() >= deadline:
            return ''
        try:
            return fetch_posting_description('SWIGGY',job['source_id'])
        except (requests.RequestException,ValueError,RuntimeError):
            return ''
    with ThreadPoolExecutor(max_workers=4) as pool:
        for job,text in zip(jobs,pool.map(description,jobs)):
            job['description']=text
    missing=sum(not job['description'] for job in jobs)
    errors = []
    if len(data['jobs']) != data['total']:
        errors.append(f"received {len(data['jobs'])} of {data['total']} feed rows")
    if invalid:
        errors.append(f"{invalid} malformed listings")
    if missing:
        errors.append(f"{missing} descriptions unavailable")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
