"""
Repost detection: catches the same underlying job posting being re-listed
under a new ATS req id (common — several boards recycle/refresh postings
every few weeks). job_id() alone can't catch this since it's keyed on the
ATS's own id, which changes on repost. This is a second, cheaper dedup
layer on top of that: same company + normalized title + city + a
description fingerprint = same job, regardless of id.

Description was added to the key after review feedback flagged a real
risk: company + title + city alone can conflate two GENUINELY DIFFERENT
concurrent postings that happen to share a title (e.g. "Data Analyst" in
Finance vs. "Data Analyst" in Marketing at the same company/city) — the
old key had no way to tell those apart and would silently drop one as a
"duplicate". Including the description (truncated/normalized, not a full
literal match) fixes that in the common case while still catching true
reposts, since a repost's description is typically unchanged or only
trivially reformatted between listings.
"""

import re

from core.location import parse_city

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

DESCRIPTION_FINGERPRINT_CHARS = 500


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
    """Cheap fingerprint of the description, used as an additional dedup
    signal (see module docstring). Not a fuzzy/semantic match — just
    whitespace-collapsed, lowercased, and truncated. Truncating (rather
    than hashing the full text) is deliberate: a genuine repost's
    description sometimes gets minor trailing edits (an added line, a
    reformatted bullet) that a full-text or full-hash comparison would
    treat as a different job, defeating the actual purpose of this
    function. The OPENING content of a posting is far more stable across
    reposts than the tail, so anchoring on the first N chars catches
    reposts more reliably than a full-text fingerprint would, while still
    distinguishing postings with genuinely different content from the
    very first sentence (the common real-world case — different
    department/team, different responsibilities)."""
    if not description:
        return ""
    d = re.sub(r"\s+", " ", description.strip().lower())
    return d[:DESCRIPTION_FINGERPRINT_CHARS]


def dedup_key(company, title, location, description=None):
    # City instead of raw location string — "Delhi" and "Delhi, India"
    # are almost certainly the same posting reformatted, but as raw
    # strings they'd produce different keys and dodge repost detection.
    # parse_city() already exists for the UI's city filter; reused here
    # for the same "extract the stable part" reasoning.
    #
    # description defaults to None/"" for backward compatibility with any
    # caller that doesn't have it handy — but every current caller
    # (run.py, storage.py's load_dedup_keys) passes it, since omitting it
    # reintroduces the false-merge risk described in the module docstring.
    return (
        company.lower(),
        normalize_title(title),
        parse_city(location).lower(),
        normalize_description(description),
    )
