"""Rippling's public careers search and public posting detail pages."""
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from fetchers.http_client import get_text, post_json
from fetchers.result import CollectionResult
from fetchers.standard import strip_html

BASE = "https://www.rippling.com"
MAX_PAGES = 100


def discover(session):
    html = get_text(session, BASE + "/careers/open-roles")
    if not html:
        raise RuntimeError("Rippling careers unavailable")
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one("#__NEXT_DATA__")
    if not node:
        raise RuntimeError("Rippling careers configuration missing")
    index = json.loads(node.string)["props"]["pageProps"]["data"]["algoliaIndexName"]
    script = next((urljoin(BASE, x["src"]) for x in soup.select("script[src]") if "/pages/_app-" in x["src"]), None)
    js = get_text(session, script) if script else None
    if not js:
        raise RuntimeError("Rippling public search configuration unavailable")
    # Discover the same client configuration the public frontend uses.
    block = js.split("46794:function", 1)[-1]
    values = []
    for symbol in ("$A", "Yi"):
        export = re.search(re.escape(symbol) + r":function\(\)\{return ([a-zA-Z_$]+)\}", block)
        assignment = re.search(r"(?:let|const|var) " + re.escape(export.group(1)) + r'="([^"]+)"', block) if export else None
        if not assignment:
            raise RuntimeError("Rippling public search configuration changed")
        values.append(assignment.group(1))
    return index, values[0], values[1]


def collect(deadline=None):
    errors, jobs, entries, total = [], {}, 0, None
    with requests.Session() as session:
        index, app, search_key = discover(session)
        headers = {"X-Algolia-Application-Id": app, "X-Algolia-API-Key": search_key}
        endpoint = f"https://{app.lower()}-dsn.algolia.net/1/indexes/{index}/query"
        for page in range(MAX_PAGES):
            if deadline is not None and time.monotonic() >= deadline:
                errors.append("listing deadline reached")
                break
            data = post_json(session, endpoint, headers=headers, json={"query": "", "hitsPerPage": 100, "page": page})
            if not isinstance(data, dict) or not isinstance(data.get("hits"), list):
                if page == 0:
                    raise RuntimeError("Rippling public search failed")
                errors.append(f"page {page} failed")
                break
            total = data.get("nbHits")
            entries += len(data["hits"])
            for hit in data["hits"]:
                locations = [loc for loc in hit.get("locations", []) if loc.get("countryCode") == "IN"]
                if not locations:
                    continue
                source_id = hit.get("jobId")
                if not source_id or not hit.get("url"):
                    errors.append("malformed India listing")
                    continue
                job = jobs.setdefault(source_id, {"company": "rippling", "source_id": source_id,
                    "title": hit.get("name", "").strip(), "location": "", "url": hit["url"], "description": ""})
                names = [loc.get("name", "") for loc in locations]
                job["location"] = "; ".join(dict.fromkeys([job["location"]] + [name + ", India" for name in names if name])).strip("; ")
            if page + 1 >= data.get("nbPages", MAX_PAGES):
                break
        else:
            errors.append("page limit reached")
        if not isinstance(total, int) or entries != total:
            errors.append(f"received {entries} of {total} search entries")

        def detail(job):
            if deadline is not None and time.monotonic() >= deadline:
                return False
            html = get_text(session, job["url"])
            node = BeautifulSoup(html or "", "html.parser").select_one("#__NEXT_DATA__")
            if not node:
                return False
            try:
                data = json.loads(node.string)["props"]["pageProps"]["apiData"]["jobPost"]
                description = data.get("description", "")
                if isinstance(description, dict):
                    description = "\n\n".join(str(v) for v in description.values() if v)
                job["description"] = strip_html(description, max_chars=None)[:12000]
            except (KeyError, TypeError, ValueError):
                return False
            return bool(job["description"])

        with ThreadPoolExecutor(max_workers=4) as pool:
            missing = sum(not ok for ok in pool.map(detail, jobs.values()))
        if missing:
            errors.append(f"{missing} descriptions unavailable or deadline reached")
    return CollectionResult(list(jobs.values()), status="partial" if errors else "ok", error="; ".join(errors))
