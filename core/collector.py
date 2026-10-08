"""
Orchestrates every fetcher into one merged job list. Company lists and
match filters live in config.py — this file only wires platform name ->
fetch function.
"""

import logging
from concurrent.futures import ThreadPoolExecutor

import config
from fetchers import career_html, tredence, myntra, makemytrip, ubs, pwc
from fetchers import qualcomm_students, morgan_stanley_students, unitedhealthgroup, zepto, hrt, bloomberg, linkedin_company, netflix, workday_india, automattic, zerodha, amd, booking, target, tesco, juspay, mediatek, millennium, ainterviews, amazon, apple, atlassian, bank_of_america, barclays, blackrock, deloitte, deshaw, deutsche_bank, eightfold, expedia, flipkart, goldman_sachs, google_careers, icims, indiamart, intuit, mastercard_workday, meta, oracle, paypal, phenom, quadeye, rippling, smartrecruiters, standard, successfactors, swiggy, tower_research, uber, workable, workday, zs
from fetchers.result import CollectionResult
log = logging.getLogger("jobbot")

# Ordered by historical yield: standard (Greenhouse/Lever/Ashby, incl. Paytm)
# and oracle (Amex) have produced 100% of real NCR matches so far. Phenom and
# Workday host huge *global* companies with many postings unrelated to NCR —
# order doesn't gate anything anymore (no post cap/time budget now that this
# runs once/day), but keeping the fast/high-yield platforms first still
# means partial logs are more useful if something fails partway through.
PLATFORMS = [
    ("pwc", lambda deadline: pwc.collect(deadline)),
    ("ubs", lambda deadline: ubs.collect(deadline)),
    ("makemytrip", lambda deadline: makemytrip.collect(deadline)),
    ("myntra", lambda deadline: myntra.collect(deadline)),
    ("tredence", lambda deadline: tredence.collect(deadline)),
    ("sap", lambda deadline: career_html.collect_sap(deadline)),
    ("lowes", lambda deadline: career_html.collect_lowes(deadline)),
    ("nutanix", lambda deadline: career_html.fetch('nutanix', deadline)),
    ("mathworks", lambda deadline: career_html.fetch('mathworks', deadline)),
    ("maqsoftware", lambda deadline: career_html.collect_maq(deadline)),
    ("micron", lambda deadline: career_html.collect_micron(deadline)),
    ("qualcomm_students", lambda deadline: qualcomm_students.collect(deadline)),
    ("workday_students", lambda deadline: workday_india.collect(config.WORKDAY_STUDENTS, deadline)),
    ("morgan_stanley_students", lambda deadline: morgan_stanley_students.collect(deadline)),
    ("unitedhealthgroup", lambda deadline: unitedhealthgroup.collect(deadline)),
    ("zepto", lambda deadline: zepto.collect(deadline)),
    ("hrt", lambda deadline: hrt.collect(deadline)),
    ("bloomberg", lambda deadline: bloomberg.collect(deadline)),
    ("linkedin_company", lambda deadline: linkedin_company.collect(deadline)),
    ("workday_india", lambda deadline: workday_india.collect(config.WORKDAY_INDIA, deadline)),
    ("netflix", lambda deadline: netflix.collect(deadline)),
    ("automattic", lambda deadline: automattic.collect(deadline)),
    ("zerodha", lambda deadline: zerodha.collect(deadline)),
    ("amd", lambda deadline: amd.collect(deadline=deadline)),
    ("booking", lambda deadline: booking.collect(deadline=deadline)),
    ("target", lambda deadline: target.collect(deadline=deadline)),
    ("tesco", lambda deadline: tesco.collect(deadline=deadline)),
    ("juspay", lambda deadline: juspay.collect(deadline=deadline)),
    ("mediatek", lambda deadline: mediatek.collect(deadline=deadline)),
    ("millennium", lambda deadline: millennium.collect(deadline=deadline)),

    ("paypal", lambda deadline: paypal.collect(deadline=deadline)),
    ("blackrock", lambda deadline: blackrock.collect(deadline=deadline)),
    ("intuit", lambda deadline: intuit.collect(deadline=deadline)),
    ("rippling", lambda deadline: rippling.collect(deadline=deadline)),
    ("deshaw", lambda deadline: deshaw.collect(deadline=deadline)),
    ("quadeye", lambda deadline: quadeye.collect(deadline=deadline)),
    ("zs", lambda deadline: zs.collect(deadline=deadline)),
    ("swiggy", lambda deadline: swiggy.collect(deadline=deadline)),
    ("tower_research", lambda deadline: tower_research.collect(deadline=deadline)),
    ("deloitte", lambda deadline: deloitte.collect(deadline=deadline)),
    ("standard", lambda deadline: standard.collect(config.GREENHOUSE, config.LEVER, config.ASHBY, deadline)),
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
