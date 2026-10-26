"""Josh Technology Group's public WordPress career list and full job pages."""
import re
import time
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import requests

from backend.core.location import parse_country
from .http_client import get_text
from .result import CollectionResult
from .standard import strip_html

BASE = 'https://www.joshtechnologygroup.com'
SEARCH_URL = BASE + '/careers/'


def _url(value, listing=False):
    parts = urlsplit(urljoin(SEARCH_URL, value))
    pattern = r'/careers/(?:page/\d+/)?' if listing else r'/careers/[a-z0-9-]+/'
    path = parts.path.rstrip('/')+'/'
    if (parts.scheme != 'https' or parts.hostname not in {'joshtechnologygroup.com', 'www.joshtechnologygroup.com'}
            or parts.username or parts.password or parts.port not in (None, 443) or not re.fullmatch(pattern, path)):
        raise ValueError('Invalid Josh Technology Group career URL')
    return BASE+path


def _list(html):
    soup = BeautifulSoup(html, 'html.parser')
    containers = soup.select('.career-list__openings')
    if not containers:
        raise ValueError('JTG careers listing layout unavailable')
    jobs, errors = {}, []
    for container in containers:
        for anchor in container.select('a[href]'):
            try:
                url = _url(anchor['href'])
            except ValueError:
                if 'career-list__opening' in anchor.get('class', []):
                    errors.append('invalid opening URL')
                continue
            title_node = anchor.select_one('p')
            title = title_node.get_text(' ', strip=True) if title_node else re.sub(r'\s+Apply$', '', anchor.get_text(' ', strip=True))
            if url in jobs:
                continue
            if not title or title.strip().lower() in {'apply', 'apply now', 'view job'}:
                errors.append('opening title unavailable')
                continue
            jobs.setdefault(url, title)
    next_link = soup.select_one('.pagination a[rel="next"], a.next.page-numbers')
    next_url = _url(next_link['href'], listing=True) if next_link and next_link.get('href') else None
    return jobs, next_url, errors


def _detail(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    canonical = soup.select_one('link[rel="canonical"][href]')
    if canonical and _url(canonical['href']) != url:
        raise ValueError('JTG detail canonical points to a different posting')
    section = soup.select_one('main .career-list')
    title = section.select_one('.career-list__title') if section else None
    bodies = section.select('.career-list__content, .career-list__openings') if section else []
    if not title or not title.get_text(' ', strip=True) or not bodies:
        raise ValueError('JTG detail title/description layout unavailable')
    # The list already exposes this identity, so a failed detail and its later
    # successful refresh use the same ID rather than creating two saved jobs.
    source_id = url.rstrip('/').rsplit('/', 1)[-1]
    texts, location = [], ''
    for body in bodies:
        for node in body.select('form, input, textarea, button, script, style, a.btn, #apply-now, #apply-now-clone'):
            node.decompose()
        for node in body.select('p, li'):
            line = node.get_text(' ', strip=True).replace('\xa0', ' ')
            match = re.match(r'^(?:(?:work|job)\s+)?locations?\s*:\s*(.*)', line, re.I)
            if match:
                location = match.group(1).strip()
                if not location:
                    adjacent = node.find_next_sibling('p')
                    value = adjacent.get_text(' ', strip=True) if adjacent else ''
                    if value and not re.match(r'^[\w ]+:', value):
                        location = value.lstrip('•· \xa0\t')
        text = strip_html(str(body), max_chars=None)
        if text:
            texts.append(text)
    description = '\n\n'.join(texts)
    if not description:
        raise ValueError('JTG full description unavailable')
    if (parse_country(location) == 'Unknown' and re.search(r'\b(gurgaon|gurugram|noida|bengaluru|bangalore|hyderabad|chennai|pune|new delhi|mumbai)\b', location, re.I)):
        location += ', India'
    return dict(company='joshtechnologygroup', source_id=source_id, title=title.get_text(' ', strip=True),
                location=location or 'Unknown', url=url, description=description)


def collect(deadline=None):
    links, errors, pages = {}, [], set()
    url = SEARCH_URL
    with requests.Session() as session:
        for _ in range(100):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('listing deadline reached')
                break
            if url in pages:
                errors.append('repeated listing page')
                break
            pages.add(url)
            try:
                html = get_text(session, url)
                if html is None:
                    raise ValueError('JTG careers request failed')
                found, next_url, issues = _list(html)
                links.update(found)
                errors.extend(issues)
            except ValueError as exc:
                errors.append(str(exc))
                break
            if not next_url:
                break
            url = next_url
        else:
            errors.append('listing page limit reached')
        if errors and not links:
            raise RuntimeError('; '.join(errors))
        jobs, seen = [], set()
        for url, title in links.items():
            fallback = dict(company='joshtechnologygroup', source_id=url.rstrip('/').rsplit('/', 1)[-1],
                            title=title, location='Unknown', url=url, description='')
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('detail deadline reached')
                job = fallback
            else:
                try:
                    html = get_text(session, url)
                    if html is None:
                        raise ValueError('detail request failed')
                    job = _detail(html, url)
                    if job['location'] == 'Unknown':
                        errors.append('location unavailable: '+title)
                    elif parse_country(job['location']) not in {'India', 'Unknown'}:
                        continue
                except ValueError as exc:
                    errors.append(title+': '+str(exc))
                    job = fallback
            if job['source_id'] not in seen:
                seen.add(job['source_id'])
                jobs.append(job)
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(dict.fromkeys(errors))[:1200])
