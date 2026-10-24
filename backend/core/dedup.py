"""Conservative duplicate evidence: full description plus the posting URL.

Different requisition URLs remain separate even when their boilerplate is
identical. Stable source IDs are handled first by storage.job_id().
"""

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.core.location import parse_city

# Only strip a 2024-2029 number when it's clearly acting as a batch/grad-year
# qualifier — parenthesized ("(2027)"), dash-prefixed ("- 2027"), or paired
# with an explicit word like "batch"/"graduates"/"class of". A bare
# standalone year anywhere else in a title (e.g. a product name, an
# unrelated identifier) is left alone. Previously any standalone 2024-2029
# number was stripped regardless of context, which is safe for the common
# "Title - 2027 Batch" case but risked stripping a meaningful number that
# happened to fall in that range for an unrelated reason.
_BATCH_YEAR_RE = re.compile(
    r"\(\s*(?:20)?2[4-9]\s*\)|"                          # "(2027)"
    r"-\s*(?:20)?2[4-9]\s*(?:batch|grad(?:uates?)?)?|"   # "- 2027" / "- 2027 batch"
    r"\b(?:20)?2[4-9]\s*(?:batch|grad(?:uates?)?)\b|"    # "2027 batch" (no dash)
    r"\bbatch\s*(?:20)?2[4-9]\b|"                        # "batch 2027"
    r"\bclass\s+of\s+(?:20)?2[4-9]\b",                   # "class of 2027"
    re.I,
)

def normalize_title(title):
    """Strip noise so the same underlying posting compares equal across
    reposts — batch-year mentions, punctuation, extra whitespace.
    e.g. "Data Analyst - 2027 Batch" and "Data Analyst (2027)" both
    normalize to "data analyst"."""
    if not title:
        return ""
    t = title.lower()
    t = _BATCH_YEAR_RE.sub("", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)       # punctuation -> space
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_description(description):
    """Hash all normalized text; shared opening boilerplate is insufficient."""
    if not description:
        return ""
    d = re.sub(r"\s+", " ", description.strip().lower())
    return hashlib.sha256(d.encode()).hexdigest() if d else ""


def canonical_job_url(url):
    """Drop campaign parameters, retaining job-ID queries and SPA fragments."""
    try:
        parts = urlsplit((url or "").strip())
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return ""
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_") and key.lower() not in {"gh_src", "lever-source", "lever-origin"}]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"),
                           urlencode(sorted(query)), parts.fragment))
    except ValueError:
        return ""


def dedup_key(company, title, location, description=None, url=None):
    return (
        (company or "").strip().lower(),
        normalize_title(title),
        parse_city(location).lower(),
        normalize_description(description),
        canonical_job_url(url),
    )
