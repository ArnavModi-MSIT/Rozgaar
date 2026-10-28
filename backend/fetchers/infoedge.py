"""Info Edge's public Zwayam feed, with full job-detail bodies and India scope."""
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
from urllib.parse import quote

from rozgaar.paths import ROOT
from .result import CollectionResult
from .standard import strip_html

COMPANY_ID = '15578'
SEARCH_URL = 'https://careers.infoedge.com/infoedge/jobslist'
MAX_PAGES = 850


class PublicRequestError(RuntimeError):
    def __init__(self, message, status=0):
        super().__init__(message)
        self.status = status


class PublicTransport:
    """One bounded native HTTP/2 helper, rather than one process per posting."""
    def __enter__(self):
        executable = shutil.which('pwsh')
        if not executable:
            candidates = [ROOT/'runtime/tools/powershell/pwsh.exe',
                Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'PowerShell/7/pwsh.exe']
            executable = next((str(path) for path in candidates if path.is_file()), None)
        if not executable:
            raise RuntimeError('Info Edge requires PowerShell 7 (pwsh). See README.md; other career sources remain independent.')
        self.process = subprocess.Popen([executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-File',
            str(ROOT/'scripts/career/zwayam_http.ps1')], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding='utf-8', bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        self.replies = queue.Queue()

        def receive():
            try:
                for line in self.process.stdout:
                    self.replies.put(line)
            finally:
                self.replies.put(None)
        self.thread = threading.Thread(target=receive, daemon=True)
        self.thread.start()
        return self

    def request(self, kind, **values):
        if self.process.poll() is not None:
            raise RuntimeError('Info Edge HTTP helper stopped')
        self.process.stdin.write(json.dumps(dict(kind=kind, **values))+'\n')
        self.process.stdin.flush()
        try:
            line = self.replies.get(timeout=25)
        except queue.Empty:
            self.process.kill()
            raise RuntimeError('Info Edge HTTP helper timed out') from None
        if line is None:
            raise RuntimeError('Info Edge HTTP helper stopped without a response')
        reply = json.loads(line)
        if reply.get('ok') is not True:
            raise PublicRequestError(reply.get('error') or 'Info Edge public request failed', reply.get('status', 0))
        return reply.get('data')

    def __exit__(self, *_):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self.process.kill()
            self.process.wait(timeout=2)
        finally:
            self.process.stdout.close()
            self.thread.join(timeout=1)


def _page(payload):
    data = payload.get('data') if isinstance(payload, dict) and payload.get('code') == 200 else None
    if not isinstance(data, dict) or not isinstance(data.get('data'), list):
        raise ValueError('Info Edge search has no valid jobs list')
    count = data.get('totalCount')
    if isinstance(count, bool) or not isinstance(count, int) or count < 0 or not isinstance(data.get('hasMoreData'), bool):
        raise ValueError('Info Edge search has no valid total/pagination state')
    return data['data'], count, data['hasMoreData']


def _identity(source):
    sid = str(source.get('id') or '')
    if str(source.get('companyId')) != COMPANY_ID or not re.fullmatch(r'\d{1,18}', sid):
        raise ValueError('Info Edge posting identity/company mismatch')
    return sid


def _location(source):
    locations, countries = [], []
    for entry in source.get('jobLocationRecord') or []:
        country = str(entry.get('country') or '').strip().lower()
        if country:
            countries.append(country)
        if country in {'india', 'in'}:
            location = entry.get('formattedLocation') or entry.get('location') or entry.get('city') or 'India'
            if not re.search(r'\bIndia\b', location, re.I):
                location += ', India'
            if location not in locations:
                locations.append(location)
    if locations:
        return '; '.join(locations)
    if countries:
        return None  # Foreign-only posting; still counted in global pagination.
    if str(source.get('country') or '').strip().lower() in {'india', 'in'}:
        return (source.get('location') or 'India') + ', India'
    raise ValueError('Info Edge posting country unverified')


def _listing(source):
    sid = _identity(source)
    location = _location(source)
    if location is None:
        return None
    title, slug = source.get('jobTitle'), source.get('jobUrl')
    if not isinstance(title, str) or not title.strip() or not isinstance(slug, str) or not slug:
        raise ValueError('Info Edge posting title/URL missing')
    return dict(company='infoedge', source_id=sid, title=title.strip(), location=location,
                url=f'https://careers.infoedge.com/infoedge/jobview/{quote(slug, safe="-")}?id={sid}', description='')


def _description(detail, sid):
    if not isinstance(detail, dict) or _identity(detail) != sid:
        raise ValueError('Info Edge detail redirected to another posting')
    sections = []
    texts = set()
    for key, label in [('longDescription', ''), ('role', 'Role')]:
        raw = detail.get(key)
        if isinstance(raw, list):
            raw = ', '.join(value for value in raw if isinstance(value, str))
        text = strip_html(raw, max_chars=None) if isinstance(raw, str) else ''
        if text and text.strip().lower() not in {'jd', 'job description', 'job description:'} and text not in texts:
            sections.append((label+':\n' if label else '')+text)
            texts.add(text)
    if not sections:
        raise ValueError('Info Edge full description missing; list preview not substituted')
    for key, label in [('eduqualification', 'Education'), ('skillSet', 'Skills'), ('desiredSkill', 'Desired skills')]:
        raw = detail.get(key)
        if isinstance(raw, list):
            raw = ', '.join(value for value in raw if isinstance(value, str))
        text = strip_html(raw, max_chars=None) if isinstance(raw, str) else ''
        if text and text not in texts:
            sections.append(label+':\n'+text)
            texts.add(text)
    # Preserve declared bounds, including minimum zero. Do not turn a maximum into a minimum.
    minimum, maximum = detail.get('minYrsOfExperience'), detail.get('maxYrsOfExperience')
    if minimum is not None:
        sections.append(f'Experience: {minimum}' + (f' to {maximum}' if maximum is not None else '+') + ' years')
    return '\n\n'.join(sections)


def collect(deadline=None):
    jobs, errors, seen = [], [], set()
    total, offset, foreign = None, 0, 0
    with PublicTransport() as transport:
        for _ in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached')
                break
            try:
                rows, count, more = _page(transport.request('search', offset=offset))
            except (ValueError, RuntimeError, OSError) as exc:
                errors.append(str(exc))
                break
            if total is not None and total != count:
                errors.append('reported total changed during pagination')
            total = count
            fresh = 0
            for hit in rows:
                try:
                    source = hit.get('_source') if isinstance(hit, dict) else None
                    if not isinstance(source, dict):
                        raise ValueError('Info Edge listing source missing')
                    sid = _identity(source)
                    if sid in seen:
                        continue
                    seen.add(sid)
                    fresh += 1
                    job = _listing(source)
                    if job:
                        jobs.append(job)
                    else:
                        foreign += 1
                except ValueError as exc:
                    errors.append(str(exc))
            offset += len(rows)
            if offset >= count and not more:
                break
            if not rows or not fresh or not more:
                errors.append('empty/repeated page or premature pagination end')
                break
            time.sleep(0.1)
        else:
            errors.append('listing page limit reached')
        if total is not None and len(seen) != total:
            errors.append(f'received {len(seen)} of {total} global postings before India filtering')
        failures = 0
        for job in jobs:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('detail deadline reached')
                break
            try:
                job['description'] = _description(transport.request('detail', id=job['source_id']), job['source_id'])
                failures = 0
            except ValueError as exc:
                # An incomplete posting is not evidence that the endpoint is down.
                errors.append(job['source_id']+': '+str(exc))
                failures = 0
            except (RuntimeError, OSError) as exc:
                errors.append(job['source_id']+': '+str(exc))
                if isinstance(exc, PublicRequestError) and exc.status in {401, 403, 429}:
                    errors.append('access restricted; stopped detail requests')
                    break
                failures = 0 if isinstance(exc, PublicRequestError) and exc.status == 404 else failures + 1
                if failures >= 3:
                    errors.append('three consecutive detail failures; stopped enrichment')
                    break
            time.sleep(0.1)
    missing = sum(not job['description'] for job in jobs)
    if missing:
        errors.insert(0, f'{missing} full descriptions unavailable')
    if errors and not jobs:
        raise RuntimeError('Info Edge: '+'; '.join(dict.fromkeys(errors))[:800])
    result = CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(dict.fromkeys(errors))[:1200])
    result.source_counts = dict(reported=total, unique=len(seen), foreign=foreign, india=len(jobs), missing_descriptions=missing)
    return result
