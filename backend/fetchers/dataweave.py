"""DataWeave official public careers and full HTML descriptions."""
import re
import time
from urllib.parse import urljoin, urlsplit
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .result import CollectionResult

BASE = 'https://dataweave.com'
SEARCH_URL = BASE + '/in/careers'

def fetch(cfg, deadline=None):
    jobs, errors = [], []
    with requests.Session() as session:
        if deadline is not None and time.monotonic() >= deadline:
            raise RuntimeError('DataWeave listing deadline reached')
        html = get_text(session, SEARCH_URL)
        soup = BeautifulSoup(html or '', 'html.parser')
        if not soup.find(string=re.compile('Current Openings')):
            raise RuntimeError('DataWeave listing layout unavailable')
        links = {}
        for a in soup.select('a[href]'):
            url = urlsplit(urljoin(BASE, a['href']))
            if url.scheme == 'https' and url.netloc == 'dataweave.com' and re.fullmatch(r'/jobs/[A-Za-z0-9-]+/[A-Za-z0-9-]+/?', url.path):
                links[url.geturl()] = a.get_text(' ', strip=True)
        for url in links:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append('detail deadline reached'); break
            try:
                page = get_text(session, url)
            except requests.RequestException:
                errors.append('detail request failed'); continue
            detail = BeautifulSoup(page or '', 'html.parser')
            body = detail.select_one('#printthis.jobcontent')
            title = body.select_one('h1') if body else None
            if not title or not title.get_text(strip=True):
                errors.append('detail unavailable'); continue
            for el in body.select('form,script,style,button,input'):
                el.decompose()
            text = body.get_text('\n', strip=True)
            match = re.search(r'Job Location:\s*([^\n]+)', text)
            if not match or not re.search(r'\bIndia\b', match[1], re.I):
                errors.append('India location unavailable'); continue
            if 'Skills & Requirements' not in text:
                errors.append('full description unavailable'); continue
            jobs.append(dict(company='dataweave', source_id=url.rstrip('/').rsplit('/',1)[-1],
                             title=title.get_text(' ',strip=True), location=match[1].strip(), url=url, description=text))
    if errors and not jobs:
        raise RuntimeError('DataWeave: ' + '; '.join(errors))
    return CollectionResult(jobs, status='partial' if errors else 'ok', error='; '.join(errors))
