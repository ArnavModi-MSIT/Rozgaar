"""
Orchestrates every fetcher into one merged job list. Company lists and
match filters live in config.py — this file only wires platform name ->
fetch function.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import config
from fetchers import ainterviews, amazon, apple, atlassian, bank_of_america, barclays, deutsche_bank, eightfold, expedia, flipkart, goldman_sachs, google_careers, icims, indiamart, internshala, linkedin, mastercard_workday, meta, oracle, phenom, smartrecruiters, standard, successfactors, uber, workable, workday
from fetchers.result import CollectionResult
log = logging.getLogger("jobbot")

# Ordered by historical yield: standard (Greenhouse/Lever/Ashby, incl. Paytm)
# and oracle (Amex) have produced 100% of real NCR matches so far. Phenom and
# Workday host huge *global* companies with many postings unrelated to NCR —
# order doesn't gate anything anymore (no post cap/time budget now that this
# runs once/day), but keeping the fast/high-yield platforms first still
# means partial logs are more useful if something fails partway through.
PLATFORMS = [
    ("standard", lambda deadline: standard.collect(config.GREENHOUSE, config.LEVER, config.ASHBY)),
    ("oracle", lambda deadline: oracle.collect(config.ORACLE, deadline=deadline)),
    ("icims", lambda deadline: icims.collect(config.ICIMS, deadline=deadline)),
    ("smartrecruiters", lambda deadline: smartrecruiters.collect(config.SMARTRECRUITERS, deadline=deadline)),
    ("successfactors", lambda deadline: successfactors.collect(config.SUCCESSFACTORS, deadline=deadline)),
    ("workable", lambda deadline: workable.collect(config.WORKABLE) if config.WORKABLE else CollectionResult(status="skipped", error="no Workable boards configured")),
    ("mastercard_workday", lambda deadline: mastercard_workday.collect(deadline=deadline)),
    ("phenom", lambda deadline: phenom.collect(config.PHENOM, deadline=deadline)),
    ("workday", lambda deadline: workday.collect(config.WORKDAY, deadline=deadline)),
    ("google_careers", lambda deadline: google_careers.collect(config.GOOGLE_CAREERS, deadline=deadline)),
    ("amazon", lambda deadline: amazon.collect(config.AMAZON, deadline=deadline)),
    ("atlassian", lambda deadline: atlassian.collect(deadline=deadline)),
    ("expedia", lambda deadline: expedia.collect(deadline=deadline)),
    ("apple", lambda deadline: apple.collect(deadline=deadline)),
    ("goldman_sachs", lambda deadline: goldman_sachs.collect(deadline=deadline)),
    ("deutsche_bank", lambda deadline: deutsche_bank.collect(deadline=deadline)),
    ("ainterviews", lambda deadline: ainterviews.collect(config.AINTERVIEWS, deadline=deadline)),
    ("indiamart", lambda deadline: indiamart.collect(config.INDIAMART, deadline=deadline)),
    ("internshala", lambda deadline: internshala.collect(deadline=deadline)),
    ("linkedin", lambda deadline: linkedin.collect(deadline=deadline)),
    ("bank_of_america", lambda deadline: bank_of_america.collect(deadline=deadline)),
    ("barclays", lambda deadline: barclays.collect(deadline=deadline)),
    ("flipkart", lambda deadline: flipkart.collect(deadline=deadline)),
    ("meta", lambda deadline: meta.collect(deadline=deadline)),
    ("uber", lambda deadline: uber.collect(deadline=deadline)),
    ("eightfold", lambda deadline: eightfold.collect(config.EIGHTFOLD, deadline=deadline)),
]


def collect_all():
    """Fetch every platform concurrently and return (jobs, failed_platforms).
    Used by debug_titles.py, which wants the full picture regardless of
    speed. run.py does NOT use this — it calls platforms one at a time via
    PLATFORMS so per-platform stats can be recorded.

    failed_platforms is returned (not just logged) so callers can make it
    visible in their own output — a "total postings fetched: N" summary
    can look deceptively complete even when several platforms silently
    failed underneath it."""
    jobs = []
    failed = []
    with ThreadPoolExecutor(max_workers=len(PLATFORMS)) as pool:
        futures = {pool.submit(fn, None): name for name, fn in PLATFORMS}
        for f in futures:
            name = futures[f]
            try:
                jobs += f.result()
            except Exception as e:
                log.exception("platform '%s' failed during collect_all(): %s", name, e)
                failed.append(name)
    return jobs, failed
