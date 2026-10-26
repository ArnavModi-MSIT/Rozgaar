"""Strict posting identity shared by discovery, checkpoints and history."""
import re
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit


def source_for_url(url):
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").removeprefix("www.")
    except ValueError:
        return None
    if host == "linkedin.com" and (parts.path.rstrip("/") == "/search/results/content"
                                   or parts.path.startswith(("/feed/update/", "/posts/"))):
        return "linkedin_posts"
    if host in {"indeed.com", "in.indeed.com", "secure.indeed.com"}:
        return "indeed"
    return {"linkedin.com": "linkedin", "internshala.com": "internshala", "naukri.com": "naukri", "instahyre.com": "instahyre", "wellfound.com": "wellfound"}.get(host)


def posting_key(url):
    if not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.username or parts.password or parts.port not in (None, 443):
            return None
        host = (parts.hostname or "").removeprefix("www.")
        if host in {"indeed.com", "in.indeed.com"} and parts.path.rstrip('/') in {'/viewjob','/rc/clk','/pagead/clk'}:
            identifiers = parse_qs(parts.query).get('jk', [])
            if len(identifiers) == 1 and re.fullmatch(r'[0-9a-fA-F]{16}', identifiers[0]):
                return 'indeed', identifiers[0].lower()
        if host == "linkedin.com":
            post = re.fullmatch(r"/feed/update/urn:li:(activity|share|ugcPost):([0-9]+)/?", unquote(parts.path))
            if not post:
                post = re.fullmatch(r"/posts/[^/]+-(activity|share|ugcPost)-([0-9]+)(?:-[^/]+)?/?", parts.path)
            if post:
                return "linkedin_posts", post.group(1) + ":" + post.group(2)
            match = re.fullmatch(r"/jobs/view/(?:[^/]*-)?([0-9]+)/?", parts.path)
            identifier = match.group(1) if match else None
            if not identifier and parts.path.rstrip("/") in {"/jobs/search", "/jobs/search-results"}:
                identifier = parse_qs(parts.query).get("currentJobId", [None])[0]
            if identifier and identifier.isascii() and identifier.isdigit():
                return "linkedin", identifier
        if host == "wellfound.com":
            match = re.fullmatch(r"/jobs/([0-9]+)(?:-[^/]+)?/?", parts.path)
            if match:
                return "wellfound", match.group(1)
        if host == "naukri.com":
            match = re.fullmatch(r"/job-listings-[^/]*-([0-9]+)/?", parts.path)
            if match:
                return "naukri", match.group(1)
        if host == "instahyre.com":
            match = re.fullmatch(r"/job-([0-9]+)(?:-[^/]+)?/?", parts.path)
            if match:
                return "instahyre", match.group(1)
        if host == "internshala.com":
            # The URL exposes a numeric suffix, not an unambiguous slug/ID delimiter.
            # Keep the whole suffix; do not guess a fixed ID length.
            match = re.fullmatch(r"/(internship|job|fresher-job)/detail/[^/]*?([0-9]+)/?", parts.path)
            if match:
                return "internshala", ("" if match.group(1) == "internship" else "job:") + match.group(2)
    except ValueError:
        pass
    return None


def canonical_job_url(url):
    key = posting_key(url)
    if not key:
        return None
    if key[0] == "linkedin":
        return f"https://www.linkedin.com/jobs/view/{key[1]}/"
    parts = urlsplit(url)
    if key[0] == 'indeed':
        return urlunsplit(('https', parts.hostname.removeprefix('www.'), '/viewjob', 'jk='+key[1], ''))
    if key[0] == "linkedin_posts":
        path = "/feed/update/urn:li:" + key[1] if parts.path.startswith("/feed/update/") else parts.path.rstrip("/")
        return urlunsplit(("https", "www.linkedin.com", path + "/", "", ""))
    if key[0] == "wellfound":
        return urlunsplit(("https", "wellfound.com", parts.path.rstrip("/"), "", ""))
    if key[0] == "instahyre":
        return urlunsplit(("https", "www.instahyre.com", parts.path.rstrip("/") + "/", "", ""))
    return urlunsplit(("https", "www.naukri.com" if key[0] == "naukri" else "internshala.com", parts.path.rstrip("/"), "", ""))
