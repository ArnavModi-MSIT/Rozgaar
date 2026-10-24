"""Public Spire career feed linked from Myntra's official careers site.

The public workspace endpoint scopes requests to this company without login.
Search pages already include full descriptions, matching public detail data.
"""
import re
import time
import requests
from backend.core.experience import extract_min_experience

from .http_client import get_json, get_text
from .result import CollectionResult
from .standard import strip_html

API = 'https://io.spire2grow.com/ies/v1/p'
PAGE_SIZE = 20


def parse_job(row):
    locations = []
    india = False
    for loc in row.get('jobLocation') or []:
        country = loc.get('country') or loc.get('countryCode') or ''
        if country.lower() in {'india', 'in'}:
            country = 'India'
            india = True
        locations.append(', '.join(str(value).strip() for value in [loc.get('city'),loc.get('state'),country] if value))
    if not india: return None
    sid = str(row.get('displayId') or '')
    if not sid or not row.get('jobTitle'): raise ValueError('Myntra job lacks identity/title')
    desc = strip_html(row.get('jobDescription') or '', max_chars=None)
    # Metadata must not disguise a missing full description as complete.
    if desc:
        description_minimum = extract_min_experience(desc)
        experience = row.get('requiredExperienceInMonths') or {}
        lower, upper = experience.get('from'), experience.get('to')
        if isinstance(lower,(int,float)) and not isinstance(lower,bool) and lower >= 0:
            years = f'{lower / 12:g}'
            if isinstance(upper,(int,float)) and not isinstance(upper,bool) and upper >= lower:
                years += f'-{upper / 12:g}' if upper != lower else ''
            desc += '\n\nRequired Qualifications\n'+years+' years of professional experience required (career-site experience field).'
            # The shared parser prioritizes explicit required sections over
            # unlabelled clauses. Keep a stronger requirement already found
            # in the original text from being masked by the metadata heading.
            if description_minimum is not None and description_minimum > lower / 12:
                desc += f'\n{description_minimum:g} years of experience required (requirement stated in the job description).'
        for mandatory, heading in [(True,'Required skills'),(False,'Preferred skills')]:
            skills = [s['skill'] for s in row.get('skills') or [] if s.get('skill') and s.get('isMandatory') is mandatory]
            if skills: desc += '\n\n'+heading+'\n'+', '.join(skills)
    return dict(company='myntra',source_id=sid,title=row['jobTitle'],location='; '.join(locations),url='https://jobs.myntra.com/jobs/'+sid,description=desc)


def collect(deadline=None):
    jobs, seen, errors, total = [], set(), [], None
    with requests.Session() as session:
        if deadline is not None and time.monotonic() >= deadline: raise RuntimeError('Myntra listing deadline reached')
        workspace = get_text(session,API+'/workspaceId',params={'domain':'jobs.myntra.com'})
        workspace = (workspace or '').strip()
        if not re.fullmatch(r'MYNTRA-[A-Za-z0-9_-]+',workspace):
            raise RuntimeError('Myntra public workspace unavailable or unexpected company')
        session.headers.update({'WorkspaceId':workspace,'language':'en','Accept':'application/json'})
        for page in range(1,501):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached'); break
            data = get_json(session,API+'/requisition/_search',params={'page':page,'size':PAGE_SIZE})
            if not isinstance(data,dict) or not isinstance(data.get('entities'),list) or not isinstance(data.get('total'),int):
                errors.append(f'listing page {page} unavailable'); break
            if total is None: total = data['total']
            elif total != data['total']: errors.append('listing total changed during pagination')
            fresh = 0
            for row in data['entities']:
                if row.get('workspaceId') != workspace:
                    errors.append('unexpected workspace in job response'); continue
                sid = str(row.get('displayId') or '')
                if not sid: errors.append('listing lacks job ID'); continue
                if sid in seen: continue
                seen.add(sid); fresh += 1
                try: job = parse_job(row)
                except ValueError as e: errors.append(str(e)); continue
                if job:
                    jobs.append(job)
                    if not job['description']: errors.append('description unavailable: '+sid)
            if len(seen) >= total: break
            if not fresh: errors.append('empty or repeated listing page'); break
            time.sleep(.3)
        else: errors.append('page limit reached')
    if total is None or len(seen) != total: errors.append(f'received {len(seen)} of {total} listings')
    if errors and not jobs: raise RuntimeError('; '.join(errors[:3]))
    return CollectionResult(jobs,status='partial' if errors else 'ok',error='; '.join(errors[:5]))
