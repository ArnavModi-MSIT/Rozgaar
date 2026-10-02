"""Juspay official careers page; explicit empty state is a successful result."""
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from .http_client import get_text
from .result import CollectionResult

def collect(deadline=None):
    jobs, errors = [], []
    base = "https://juspay.io/careers"
    with requests.Session() as session:
        html = get_text(session, base)
        if not html: raise RuntimeError("Juspay careers page unavailable")
        soup = BeautifulSoup(html, "html.parser")
        links = {urljoin(base, a["href"]): a for a in soup.select('a[href]') if a["href"].startswith("/careers/")}
        if not links:
            if "No global job openings available" in soup.get_text(): return CollectionResult()
            raise RuntimeError("Juspay careers markup changed: no listings or explicit empty state")
        for url in links:
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("deadline reached"); break
            detail = get_text(session, url)
            if not detail: errors.append("detail unavailable"); continue
            page = BeautifulSoup(detail, "html.parser")
            main = page.select_one("main")
            title = page.select_one("h1")
            if not main or not title: errors.append("invalid detail markup"); continue
            jobs.append({"company":"juspay", "source_id":url.rsplit("/",1)[-1], "title":title.get_text(" ",strip=True), "location":"", "url":url, "description":main.get_text(" ",strip=True)[:10000]})
            errors.append("location parsing requires verification for new Juspay markup")
    return CollectionResult(jobs, status="partial" if errors else "ok", error="; ".join(errors))
