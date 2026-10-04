"""
Filtering and relevance scoring for collected job postings.
"""

import config


def matches(job):
    # Seniority words in the title are not an eligibility gate.
    if not config.LOCATION.search(job.get("location") or ""):
        return False
    # Some companies (large BPO/consulting firms) post across every
    # function and would otherwise flood results with irrelevant roles —
    # see config.RELEVANCE_FILTERS for why.
    relevance = config.RELEVANCE_FILTERS.get(job["company"])
    if relevance and not relevance.search(job["title"]):
        return False
    return True


# NOTE: matches() is no longer called by run.py — run.py now saves every
# fetched job so resume-based matching (core/matcher.py) has the full pool
# to rank against. Left here in case you want a hard pre-filter again later.
