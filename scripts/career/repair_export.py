"""Create a separately labelled repaired JSON; never edit database snapshots/state.

Run: python -m scripts.career.repair_export --latest
Only missing/insufficient descriptions are fetched, with two concurrent requests.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import html as html_utils
from functools import lru_cache
from threading import Lock
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlparse

import requests
from backend.core.description_quality import annotate_jobs, description_quality
from backend.fetchers.career_html import structured_job
from backend.fetchers.standard import strip_html
from backend.fetchers import icims
from bs4 import BeautifulSoup
from backend.core.experience import extract_min_experience, extract_preferred_experience
from backend.core.skills import extract_skills
from rozgaar.paths import CAREER_DB, RUNTIME

_listing_lock = Lock()


@lru_cache(maxsize=4)
def icims_descriptions(host):
    """Bounded public listing scan; match requisition IDs, never title similarity."""
    result = {}
    for page in range(1, 21):
        data = icims._fetch_page(host, page, '/api/jobs', 'country=India')
        if not isinstance(data, dict):
            break
        before = len(result)
        for item in data.get('jobs') or []:
            row = item.get('data', item)
            sid = str(row.get('req_id') or '')
            if sid:
                result[sid] = strip_html(row.get('description') or '', max_chars=None)
        if len(result) == before or (data.get('totalCount') and len(result) >= data['totalCount']):
            break
    return result


def retrieve(job):
    url = job['url']
    parsed = urlparse(url)
    sid = job['id'].split(':', 1)[-1]
    evidence = {'checked_at': datetime.now(timezone.utc).isoformat(), 'url': url}
    text = ''
    with requests.Session() as session:
        session.headers['User-Agent'] = 'Mozilla/5.0'
        if re.fullmatch(r'[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com', parsed.hostname or ''):
            tenant = parsed.hostname.split('.')[0]
            parts = parsed.path.strip('/').split('/')
            index = parts.index('job')
            site = parts[index-1]
            endpoint = f'https://{parsed.hostname}/wday/cxs/{tenant}/{site}/' + '/'.join(parts[index:])
            response = session.get(endpoint, headers={'Referer':url, 'Accept':'application/json'}, timeout=20)
            evidence.update(url=endpoint, http_status=response.status_code)
            response.raise_for_status()
            row = response.json().get('jobPostingInfo') or {}
            if str(row.get('jobReqId')) == sid:
                text = strip_html(row.get('jobDescription') or '', max_chars=None)
        elif parsed.hostname == 'careers.spglobal.com':
            with _listing_lock:
                text = icims_descriptions(parsed.hostname).get(sid, '')
            evidence['url'] = f'https://{parsed.hostname}/api/jobs?country=India'
        elif parsed.hostname in {'ibqbjb.fa.ocs.oraclecloud.com', 'egug.fa.us2.oraclecloud.com'}:
            endpoint = f'https://{parsed.hostname}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails'
            response = session.get(endpoint, params={'onlyData':'true','expand':'all','finder':'ById;Id='+sid}, timeout=20)
            evidence.update(url=response.url, http_status=response.status_code)
            response.raise_for_status()
            rows = response.json().get('items') or []
            if rows and str(rows[0].get('Id')) == sid:
                text = '\n\n'.join(strip_html(rows[0].get(key) or '', max_chars=None) for key in
                    ('ExternalDescriptionStr','ExternalResponsibilitiesStr','ExternalQualificationsStr'))
        elif parsed.hostname == 'jobs.standardchartered.com':
            url = html_utils.unescape(url).replace('-en_US', '-en_GB')
            response = session.get(url, timeout=20)
            evidence.update(url=url, http_status=response.status_code)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            node = soup.select_one('[data-careersite-propertyid="description"], [itemprop="description"]')
            # Requisition number must be present in the actual detail body.
            if node and re.search(r'Requisition\s+Number:\s*'+re.escape(sid)+r'\b', soup.get_text(' ', strip=True)):
                text = strip_html(node.decode_contents(), max_chars=None)
                evidence['canonical_url'] = url
        elif parsed.hostname in {'jobs.ericsson.com','careers.qualcomm.com','morganstanley.eightfold.ai','talent.lowes.com','joblist.klimb.io'}:
            response = session.get(url, timeout=20)
            evidence['http_status'] = response.status_code
            if response.status_code == 410:
                evidence['result'] = 'source_no_longer_available'
            elif response.ok:
                for row in structured_job(response.text):
                    actual = urlparse(row.get('url') or '')
                    if actual.hostname == parsed.hostname and actual.path.rstrip('/') == parsed.path.rstrip('/'):
                        text = strip_html(row.get('description') or '', max_chars=None)
                        break
        else:
            evidence['result'] = 'no_verified_detail_adapter'
    return text, evidence


def repair_job(job):
    if description_quality(job.get('description')) == 'available':
        return job
    try:
        text, evidence = retrieve(job)
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        text, evidence = '', {'result':'request_or_parse_failed', 'error':str(exc)}
    if description_quality(text) == 'available':
        if evidence.get('canonical_url'):
            evidence['previous_url'] = job['url']
            job['url'] = evidence['canonical_url']
        job['description'] = text
        job['skills'] = sorted(extract_skills(text))
        job['required_experience_years'] = extract_min_experience(text)
        job['preferred_experience_years'] = extract_preferred_experience(text)
        job['resume_match_pct'] = None
        evidence['result'] = 'description_recovered'
    else:
        evidence.setdefault('result', 'description_unavailable')
    job['description_repair'] = evidence
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--latest', action='store_true')
    source.add_argument('--filename', help='Exact stored export filename, so a newer batch cannot change the repair target.')
    source.add_argument('--input', type=Path)
    args = parser.parse_args()
    if args.latest or args.filename:
        with sqlite3.connect(f'file:{CAREER_DB.as_posix()}?mode=ro', uri=True) as conn:
            row = conn.execute('SELECT payload_json FROM career_exports WHERE filename=?', (args.filename,)).fetchone() if args.filename else conn.execute('SELECT payload_json FROM career_exports ORDER BY created_at DESC,rowid DESC LIMIT 1').fetchone()
            if not row:
                parser.error('No matching export snapshot was found.')
            payload = json.loads(row[0])
    else:
        payload = json.loads(args.input.read_text(encoding='utf8'))
    original = payload['filename']
    with ThreadPoolExecutor(max_workers=2) as pool:
        payload['jobs'] = list(pool.map(repair_job, payload['jobs']))
    payload['description_quality_summary'] = annotate_jobs(payload['jobs'])
    payload['derived_from'] = original
    payload['filename'] = Path(original).stem + '-descriptions-reviewed.json'
    payload['repair_note'] = 'Separate reviewed copy. Original snapshot and database are unchanged. Quality labels are heuristics, not eligibility decisions. Recovered descriptions invalidate old resume scores.'
    output = RUNTIME / 'artifacts' / payload['filename']
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
    print(output)
    print(json.dumps(payload['description_quality_summary']))
    print('Recovered:', sum(j.get('description_repair', {}).get('result') == 'description_recovered' for j in payload['jobs']))


if __name__ == '__main__':
    main()
