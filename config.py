"""
Shared config: which companies to poll, and the intern/fresher + NCR filters.
Edit this file to add companies or tune matching — fetchers and run.py don't change.
"""

import re

# Salesforce posts ~1500 roles globally, most unrelated to Data/Analytics —
# same "narrow to the relevant subset before detail-fetching" reasoning as
# GENPACT_RELEVANT above, just scoped to this project's target roles
# directly rather than needing a broader BPO-function exclusion.
SALESFORCE_RELEVANT = re.compile(
    r"\b(data analyst|analytics engineer|business intelligence|\bbi\b|"
    r"data engineer|data scientist)\b", re.I,
)

# --- Greenhouse / Lever / Ashby slugs -----------------------------------------
# Verified live via debug/check_slugs.py. Re-run it before adding more.
# NOTE: check_slugs.py only confirms a slug exists on a board — it can't tell
# WHICH company owns it. Slugs aren't globally unique across ATS platforms.
# "bluestone" (Greenhouse), "porter" (Lever), and "slice" (Greenhouse) all
# resolved to unrelated US companies, not the Indian brands with the same
# name — always spot-check a few job titles/locations in debug/debug_titles.py
# before trusting a new slug, especially for common English-word names.
# ("slice" fintech's real careers site runs on Kula, not Greenhouse at all —
# confirmed via slice.bank.in/careers/open-positions -> careers.kula.ai/slice)
# NOTE: boards-api.greenhouse.io is Greenhouse's single, unified Job Board
# API regardless of which regional domain (job-boards.eu.greenhouse.io vs
# job-boards.greenhouse.io) a company's public board happens to live on —
# there is no separate "boards-api.eu.greenhouse.io" host. (Confirmed the
# hard way: it doesn't resolve in DNS.) A plain slug string always uses the
# one real API host; no region tuple needed.
GREENHOUSE = [
    "commvault", "sigmoid",
    "fanaticsinc", "fanaticscommerce", "fanaticsfbg", "fanaticscollectibles",
    "roku", "gleanwork", "okta", "purestorage", "gitlab", "squarepointcapital", "quberesearchandtechnologies",
    "alphagrepsecurities", "nksecuritiesresearch", "worldquant", "imc", "optiverus", "mongodb", "datadog",
    "arcesiumllc",
    "gravitonresearchcapital",  # Board linked by Graviton careers. 
    "airbnb",  # Official India careers page IDs match this public board. 
    # Postman uses WORKDAY_INDIA; PhonePe uses SmartRecruiters.
    "groww", "razorpaysoftwareprivatelimited", "thoughtworks",
    # Added after cross-referencing santifer/career-ops's company list against
    # real India presence (verified via web search + debug/check_slugs.py —
    # see chat history). Confirmed real India offices for both:
    "anthropic",  # 439 postings live, Bengaluru office opened Feb 2026
    "dialpad",    # 92 postings live, Bangalore office (has intern postings)
    # Added after researching top fresher-salary/growth companies with real
    # India presence not yet in this list — each confirmed via a LIVE fetch
    # against the real Greenhouse API + spot-checked India-location postings
    # (not just a slug existing), same bar as anthropic/dialpad above:
    "stripe",     # 580 postings, real Bengaluru roles (e.g. "Account
                  # Executive, Startups Hunter (India)")
    "databricks", # 829 postings, Bengaluru/Mumbai + several "Remote - India"
                  # roles (e.g. "AI Engineer - FDE", "Director of Engineering")
    "rubrik",     # 128 postings, Bengaluru/Bangalore + Mumbai roles (e.g.
                  # "Architect, AI Data Platform & Engineering")
    "coinbase",   # 182 postings, Bangalore/Hyderabad/Remote-India roles,
                  # incl. a "Country Director, India" — real local presence,
                  # not just remote-anywhere postings routed through India
    # Both had been sitting in the "checked but unconfirmed" note below
    # since an earlier pass — confirmed now via live fetch:
    "twilio",  # 141 postings, 15 India-matched, all "Remote - India"
               # (e.g. "Applications Engineer 2", "Principal Engineer (L5)")
    "vercel",  # 88 postings, 4 India-matched, all "Remote - India"
    # Zscaler — the user's own careers.zscaler.com page proxies through a
    # custom "/api/get-greenhouse-jobs" wrapper (found via a real network
    # capture), but the standard public boards-api.greenhouse.io endpoint
    # works directly with the plain slug — no custom fetcher needed.
    "zscaler",  # 348 postings, 61 real India (excl. a real Indiana mix-up
                # in a naive substring check — the actual is_india_or_unknown()
                # correctly separates them), 5 NCR (Gurgaon — Sales Engineer,
                # AI Security Specialist, Account Executive Data Security)
]
LEVER = ["meesho", "cred", "paytm", "fampay", "zeta", "netomi", "portcast"]
ASHBY = [
    "confluent",
    "navi", "sarvam",
    # 746 postings live (debug/check_slugs.py) — India presence NOT
    # independently confirmed, unlike anthropic/dialpad above. Worth
    # checking via `python debug/debug_titles.py --company openai` after
    # the next run; drop it if it's not yielding real India matches.
    "openai",
    # Confirmed via live fetch: 135 postings, real Hyderabad roles (e.g.
    # "Software Engineer, Infrastructure", "Engineering Manager, Content
    # Onboarding") — same verification bar as the Greenhouse additions above.
    "notion",
    # Snowflake — fingerprinted from the user's own careers.snowflake.com
    # URL (a Phenom People front-end over a real Ashby tenant underneath:
    # ashbyhq.com/snowflake). Its own location strings use an "IN-City"
    # ISO-country-code-prefix format none of the other Ashby companies
    # above use — core/location.py's parse_country() gained a narrow,
    # anchored fix for this (see that file's own comment for the real
    # India/Indiana collision check done before adding it). Confirmed
    # live: 18 real India postings (Pune/Bangalore/Mumbai — Technical
    # Architect AI/ML, Senior Software Engineer Fullstack), 2 NCR (Delhi-
    # Remote, both sales/partner roles).
    "snowflake",
]

# --- Checked and explicitly ruled out (real board, but no India presence) ------
# Both confirmed live via the same GREENHOUSE/LEVER-style fetch, both 0/hundreds
# of postings anywhere India-located — not slug typos, genuinely no India office
# as of this check. Documented so they aren't re-investigated from scratch later:
#   Greenhouse: "janestreet" (234 postings, 0 India — hires IIT students but for
#     non-India offices)
#   Lever: "palantir" (307 postings, 0 India — no confirmed India office)

# --- Not yet added, checked but unconfirmed / low-confidence -----------------
# Live and real (checked via debug/check_slugs.py) but India relevance is
# either unconfirmed or actively doubtful. Uncomment individually and re-run
# debug/check_slugs.py + debug/debug_titles.py --company <slug> to verify
# before trusting any of these to actually contribute India matches:
#   Greenhouse: "talkdesk2" (53 — note the "2", not "talkdesk"), "liveperson"
#     (16, thin)
#   Ashby: "cohere" (144 postings, but cohere.com's own careers page lists
#     no India office — likely a dead end), "pinecone" (8, thin regardless)
#   Workable: "huggingface" (7 postings, small NYC/Paris company, doubtful)
#     — config.WORKABLE is currently empty; this would be its first entry
#     if you want to confirm the Workable fetcher against a real board.
# (twilio/vercel moved up into GREENHOUSE above — confirmed India-relevant.)

# --- Oracle Recruiting Cloud (ORC) --------------------------------------------
# Config per company: {tenant, datacenter, site} pulled from their careers URL:
#   https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs
#     tenant=egug  datacenter=us2  site=CX_1
ORACLE = [
    {"company": "amex", "tenant": "egug", "datacenter": "us2", "site": "CX_1", "location_id": "300000000228786"},
    # No "datacenter" key — JPMC's host is tenant.fa.oraclecloud.com, not
    # tenant.fa.DATACENTER.oraclecloud.com like Amex's (confirmed via
    # debug/debug_oracle_jpmc.py). location_id scopes the fetch to India
    # server-side (confirmed: cuts 7278 global postings down to 434).
    {"company": "jpmc", "tenant": "jpmc", "site": "CX_1001", "location_id": "300000000289360"},
    # Oracle itself — fingerprinted from the user's own careers.oracle.com
    # URL (a branded frontend; the real API host and site number
    # (eeho.fa.us2.oraclecloud.com, CX_45001) were found via a regex
    # search of the page's own embedded script references). location_id
    # taken straight from the user's URL, confirmed working server-side:
    # 178 real India postings. 11 NCR (multi-location postings genuinely
    # listing Noida/Gurugram alongside other hubs, plus a Delhi/Noida-
    # specific Oracle SOA Developer role) — real engineering volume from
    # a genuine top-tier platform company, not a staffing/services firm.
    {"company": "oracle", "tenant": "eeho", "datacenter": "us2", "site": "CX_45001",
     "location_id": "300000000106947"},
    # Dell — fingerprinted from the user's own enterpriseplatform.dell.com
    # URL. A different ORC deployment shape than every other entry here:
    # Dell maps the whole product onto its own custom domain instead of a
    # tenant.fa.DATACENTER.oraclecloud.com hostname, so fetchers/oracle.py
    # gained a new optional "base_url" cfg key to bypass the tenant/
    # datacenter host construction entirely. The user's own URL carried a
    # location_id (300000000471053) that turned out to scope to a single
    # city, not all of India (14 postings scoped vs. 154 unscoped +
    # client-side is_india_or_unknown()) — left unscoped here for the
    # fuller number, same pattern as NVIDIA/Intel/Samsung. 154 real India
    # postings, genuine tech roles (Senior Postgres Platform Engineer,
    # Software Principal Engineer C++, Senior Advisor Data Science). Only
    # 1 NCR hit (Gurugram, non-tech sales) — added for the real India-wide
    # volume, same "broad India, not NCR-exclusive" precedent as Visa/
    # NVIDIA above.
    {"company": "dell", "base_url": "https://enterpriseplatform.dell.com", "site": "CX_1001"},
]

# --- Google Careers --------------------------------------------------------------
# Google's own bespoke careers platform (not a common ATS) — confirmed
# server-rendered via debug/debug_google_careers.py, card class "sMn82b".
# target_levels mirror the site's own multi-select experience-level
# filter checkboxes.
GOOGLE_CAREERS = [
    {"company": "google", "location": "India", "target_levels": ["EARLY", "INTERN_AND_APPRENTICE"]},
]

# --- Amazon Jobs -----------------------------------------------------------------
# Confirmed via debug/debug_amazon.py: the public search page has no data
# in raw HTML, but amazon.jobs/en/search.json (same query params) returns
# complete structured data directly — full description, qualifications,
# clean location. Read the full India search without keywords, preserving
# industry_experience from the user's URL. Source filters do not guarantee
# fresher eligibility; local experience and relevance filters still apply.
AMAZON = [
    {"loc_query": "India", "country": "IND", "industry_experience": "less_than_1_year"},
    # Student searches intentionally omit the industry-experience facet.
    {"loc_query": "India", "country": "IND", "base_query": "intern"},
    {"loc_query": "India", "country": "IND", "base_query": "apprentice"},
]

# --- Phenom People --------------------------------------------------------------
# Config per company: {domain, refnum, locale}. domain = the careers site
# host, e.g. "careers.mastercard.com". refnum can usually stay "" (empty)
# for single-tenant domains — the domain itself scopes the company. Only
# multi-brand Phenom deployments need a real refnum (see fetchers/phenom.py
# discover_refnum() to pull one from a site's page source if "" returns 0).
# locale = the URL path prefix the site actually uses (check the real
# careers URL, e.g. careers.mastercard.com/us/en/... -> locale="us/en").
# Used only as a fallback when the API doesn't supply its own job URL.
PHENOM = [
    # Confirmed working via debug/debug_adobe_phenom.py — 772 real
    # postings, refnum="" (single-tenant domain, no discovery needed).
    {"company": "adobe", "domain": "careers.adobe.com", "refnum": "", "locale": "us/en"},
    # Confirmed working via debug/debug_bcg_phenom.py — 874 real postings,
    # refnum="" (single-tenant), locale="global/en" per the site's own URLs.
    {"company": "bcg", "domain": "careers.bcg.com", "refnum": "", "locale": "global/en"},
    # Fiserv — found via the same careers-host fingerprint sweep as
    # Ericsson/S&P Global. Confirmed live: 507 postings, 197 of them
    # India-or-unknown. NOTE the honest caveat — despite Fiserv having a
    # Noida office, its India hiring here is overwhelmingly Pune/Thane and
    # only ONE posting was NCR at time of checking. Added for the India
    # filter's sake, not as an NCR source; drop it if the India-wide view
    # isn't useful to you.
    {"company": "fiserv", "domain": "careers.fiserv.com", "refnum": "", "locale": "us/en"},
    # Mastercard — this domain was already sitting in this file's own
    # docstring example above (careers.mastercard.com) but never actually
    # added. Confirmed live from the user's own URL: 1112 global postings,
    # 456 India, 40 NCR (8.8%) — all Gurgaon, and genuinely strong data/
    # analytics signal (Senior Data Scientist x2, AI Engineer, Senior Data
    # Analyst, Associate Analyst Analytics & Metrics). One of the best
    # finds this session — real Gurgaon Tech Hub volume in exactly the
    # role family this board targets. The separate mastercard_workday
    # collector now covers its India Workday site; shared requisition IDs
    # deduplicate overlaps while this feed retains Phenom-only jobs.
    {"company": "mastercard", "domain": "careers.mastercard.com", "refnum": "", "locale": "us/en"},
]

WORKDAY = [
    {"company": "fractal", "tenant": "fractal", "wd_server": "wd1", "site": "Careers", "fetch_details": True},
    # Fidelity International — confirmed via debug/debug_fidelity.py:
    # applied_facets locationCountry (India GUID) filters server-side,
    # 109 global -> 26 India. Small volume, safe to detail-fetch all.
    # Note: this tenant leaves locationsText null (location falls back to
    # bulletFields, and may still be blank) — the facet already guarantees
    # India, so blank locations pass the save-time is_india_or_unknown check.
    {"company": "fidelity", "tenant": "fil", "wd_server": "wd3", "site": "001",
     "applied_facets": {"locationCountry": ["c4f78be1a8f14da0ab49ce1162348a5e"]},
     "fetch_details": True},
    # Sprinklr — confirmed via debug/debug_sprinklr.py: 89 global -> 33
    # India with the same India GUID (which also confirmed the GUID is
    # shared reference data portable across ALL Workday tenants). Sample
    # included Gurgaon intern postings. Small volume, detail-fetch all.
    {"company": "sprinklr", "tenant": "sprinklr", "wd_server": "wd1", "site": "careers",
     "applied_facets": {"locationCountry": ["c4f78be1a8f14da0ab49ce1162348a5e"]},
     "fetch_details": True},
    {"company": "salesforce", "tenant": "salesforce", "wd_server": "wd12",
     "site": "External_Career_Site", "fetch_details": True},
    {"company": "nvidia", "tenant": "nvidia", "wd_server": "wd5", "site": "NVIDIAExternalCareerSite"},
    {"company": "intel", "tenant": "intel", "wd_server": "wd1", "site": "External"},
    {"company": "samsung", "tenant": "sec", "wd_server": "wd3", "site": "Samsung_Careers"},
    # HP and Medtronic — verified live via a real 787/1186-row unscoped
    # pagination each (limit=20, matching this file's other unscoped
    # Workday entries), then client-side filtered for a real India location
    # string. HP: 60/787 India (7.6%), concentrated in Bengaluru — real
    # tech roles seen (Data Engineer, Android Framework Engineer, SAP
    # Solution Architect, Technical Support Engineer). Medtronic: 109/1186
    # India (9.2%), concentrated in Hyderabad (Nanakramguda) — real tech
    # roles seen (Senior/Principal Enterprise Software Engineer, Enterprise
    # Software Test Engineer). Both tried HP's own tenant-specific facet
    # key first (HP's own /jobs response names it "Location_Country", not
    # the usual "locationCountry" — a genuinely different key name per
    # tenant, not just a different GUID) — worked once, then 400'd on an
    # identical retry, so it's not reliable enough to build on. Left
    # unscoped with client-side is_india_or_unknown() instead, same
    # pattern as NVIDIA/Intel/Samsung above. Only 2 NCR hits for HP
    # (Gurugram — Category Sales, Head of Marketing Strategy, both
    # non-tech) and 8 for Medtronic (Gurgaon — all Sales/Territory Manager,
    # non-tech); added anyway for the real India-wide tech volume, same
    # "broad India, not NCR-exclusive" precedent as NVIDIA/Intel/Samsung.
    {"company": "hp", "tenant": "hp", "wd_server": "wd5", "site": "ExternalCareerSite"},
    {"company": "medtronic", "tenant": "medtronic", "wd_server": "wd1", "site": "MedtronicCareers"},
    # Text search is bounded but includes US and ambiguous locations.
    # Walmart IND/USA title and IN location prefixes are normalized in the fetcher.
    {"company": "walmart", "tenant": "walmart", "wd_server": "wd504", "site": "WalmartExternal",
     "search_text": "Global Tech India", "fetch_details": True},
    # Adobe was fingerprinted here too (adobe.wd5.myworkdayjobs.com/
    # external_experienced, 739 postings, 45 NCR) before realizing
    # config.PHENOM already has a working "adobe" entry — careers.adobe.com
    # is a Phenom People front-end over the SAME underlying Workday data,
    # and that pre-existing entry actually surfaces it slightly better
    # (687 jobs, 53 NCR — same real roles: Computer Scientist, Machine
    # Learning Engineer, Software Development Engineer). Adding it again
    # here would just double-count every Adobe posting in the db, so it's
    # deliberately NOT added — see PHENOM above for the real entry.
    # Visa — the user's own URL already carried the shared India
    # locationCountry facet GUID applied client-side
    # (visa.wd5.myworkdayjobs.com/Visa?locationCountry=c4f7...), and unlike
    # HP's flaky version of this same facet (worked once, then 400'd on an
    # identical retry — see HP's note above), Visa's held up cleanly
    # across repeated calls. 65 real India postings, all Bengaluru/Mumbai
    # — genuinely relevant tech roles (Staff Software Engineer, Sr.
    # Manager Data Reliability Engineering, QA Automation/SRE, Software
    # Engineer with AI/GenAI). Zero NCR presence in the full set (all 65
    # checked, not a sample) — added anyway for the real India-wide tech
    # volume, same "broad India, not NCR-exclusive" precedent as
    # NVIDIA/Intel/Samsung/Walmart above. Server-side scoped via
    # applied_facets since the facet reliably works here, unlike those.
    {"company": "visa", "tenant": "visa", "wd_server": "wd5", "site": "Visa",
     "applied_facets": {"locationCountry": ["c4f78be1a8f14da0ab49ce1162348a5e"]}},
    # Cisco — fingerprinted from the user's own careers.cisco.com URL
    # (a Phenom People-built front-end, same shape as the Adobe case
    # above, over a real Workday tenant underneath: cisco.wd5.myworkdayjobs.com/
    # Cisco_Careers). Confirmed live: 1221 global postings, 785 India-or-
    # unknown — huge volume. Only 3 NCR hits (Gurgaon, all sales/account-
    # executive roles), so this is squarely a "broad India tech volume"
    # add, same precedent as NVIDIA/Intel/Visa above, not an NCR source.
    {"company": "cisco", "tenant": "cisco", "wd_server": "wd5", "site": "Cisco_Careers"},
    {"company": "autodesk", "tenant": "autodesk", "wd_server": "wd1", "site": "Ext",
     "applied_facets": {"locationCountry": ["c4f78be1a8f14da0ab49ce1162348a5e"]}},
    # Palo Alto Networks — fingerprinted from the user's own
    # jobs.paloaltonetworks.com URL, which links out to a real Workday
    # tenant (paloaltonetworks.wd5.myworkdayjobs.com/panwexternalcareers).
    # Confirmed live: 1448 global postings, 153 real India (Bangalore/Pune
    # — Principal Engineer Software, Staff IT SRE, QA Lead), 5 NCR. Real
    # cybersecurity engineering volume from a genuine top-tier company.
    {"company": "paloaltonetworks", "tenant": "paloaltonetworks", "wd_server": "wd5", "site": "panwexternalcareers", "fetch_details": True},
]

# --- Eightfold PCSX ---------------------------------------------------------------
# apply.{company}.com portals — confirmed via debug/debug_ukg.py:
# /api/pcsx/search is open unauthenticated, location param filters
# server-side (location=India returned only Pune/Noida/Bangalore roles).
# Descriptions NOT available (match_details needs an authenticated
# session) — list-only, "Department: X" stored as minimal description,
# same trade-off as Expedia.
EIGHTFOLD = [
    {"company": "ukg", "host": "apply.ukg.com", "domain": "ukg.com", "location": "India"},
    # Microsoft India, limited to the requested Intern and Entry levels.
    # PCSX does not decode the comma-separated seniority value correctly.
    # Separate searches implement the Intern OR Entry selection.
    {"company": "microsoft", "host": "apply.careers.microsoft.com", "domain": "microsoft.com", "location": "India", "sort_by": "distance", "filter_seniority": "Intern", "filter_include_remote": "1", "filter_include_relocation": "0"},
    {"company": "microsoft", "host": "apply.careers.microsoft.com", "domain": "microsoft.com", "location": "India", "sort_by": "distance", "filter_seniority": "Entry", "filter_include_remote": "1", "filter_include_relocation": "0"},
    # Ericsson — found by fingerprinting careers hosts for a KNOWN platform
    # signature rather than guessing slugs (see the S&P Global note in
    # ICIMS below for why that method replaced the old one). Confirmed
    # live: location=India returns 140 postings, heavily Noida — one of
    # the better NCR yields in this file. No new code needed.
    {"company": "ericsson", "host": "jobs.ericsson.com", "domain": "ericsson.com", "location": "India"},
    # Qualcomm — one of the highest-paying employers in India and a real
    # NCR presence (Noida). Previously listed in this file as unsolved
    # after guessing Workday tenants (every combination 422'd, and the one
    # that answered returned total=0) — it was never Workday at all. Its
    # real careers URL (careers.qualcomm.com/careers?start=0&sort_by=timestamp)
    # carries the Eightfold PCSX signature plainly, so this needed no new
    # code, only the right platform. A good reminder that a failed GUESS
    # at one platform says nothing about which platform a site actually uses.
    # Confirmed live: location=India returns 555 postings; 21 NCR (14 Noida)
    # in the 500 fetched. Bangalore/Hyderabad-heavy and mostly hardware/
    # silicon engineering, so treat the NCR slice, not the total, as the
    # value here.
    {"company": "qualcomm", "host": "careers.qualcomm.com", "domain": "qualcomm.com", "location": "India"},
    {"company": "morganstanley", "host": "morganstanley.eightfold.ai", "domain": "morganstanley.com", "location": "India"},
]

# --- SAP SuccessFactors -----------------------------------------------------------
# The RMK/"Career Site Builder" public front-end — see
# fetchers/successfactors.py's module docstring for the full investigation
# (no public API exists; this scrapes the site's own /search/ listing,
# which exposes title/location/href as clean separate fields).
#
# Built specifically because a survey of ~30 Indian-origin/NCR companies
# found most of them are NOT on any ATS this project already supported;
# SuccessFactors was the most common of the unsupported ones and the only
# one with a confirmed-accessible public surface.
#
# Config per company: {company, host, fetch_details (optional)}.
#   host = the career site host, taken straight from the real careers URL
#          (e.g. payu.in/careers redirects to careers.payu.in).
#   fetch_details = opt-in per-job description fetch, India/unknown-gated
#          — same volume reasoning as WORKDAY's flag of the same name.
SUCCESSFACTORS = [
    # PayU — Gurugram-HQ'd. Confirmed live: 138 postings total, 43 of them
    # NCR (Gurgaon 41 / Noida 2) — a ~31% NCR yield, by far the highest of
    # any single company in this file. Small enough volume to safely
    # detail-fetch every India/unknown posting.
    {"company": "payu", "host": "careers.payu.in", "fetch_details": True},
    {"company": "standardchartered", "host": "jobs.standardchartered.com",
     "category_id": 9783657, "variant": "rmk",
     "facet_filters": {"jobLocationCountry": ["India"]}},
]

# --- Investigated, NOT built: Darwinbox and Keka ---------------------------------
# Both were checked right after fetchers/successfactors.py was built, since
# the same survey that motivated it found these two as the other common
# platforms among Indian-origin/NCR companies. Neither is currently
# buildable. Recorded here so the investigation isn't repeated blind.
#
# DARWINBOX (e.g. dbx.darwinbox.in/ms/candidatev2/main/careers/allJobs):
#   Angular SPA — zero job data in the raw HTML. Its documented API
#   (api-docs.darwinbox.com, /JobsApiv3/...) is Basic-Auth/OAuth 2.0 and
#   employer-side only, not a public job board feed. Its JS bundles expose
#   only Angular ROUTE paths, no API endpoints (calls are built at
#   runtime), and every guessed API path returns the SPA shell because the
#   host catch-all routes everything. GET /sitemap.xml returns 403 from a
#   bot-protection interstitial — the same signature as the ZS Associates
#   case documented in ICIMS below, which this project already decided
#   isn't worth chasing without a headless browser. Same call here.
#
#   CLOSED, definitively, via a second real tenant (Delhivery,
#   delhivery.darwinbox.in): the real job-list endpoint IS findable via a
#   Playwright network capture — POST {tenant}.darwinbox.in/ms/
#   candidateapi/job/alljobs?companyId=main, body {"companyId":"main",
#   "page":1,"sort_option":"new","limit":10} — and it DOES generalize
#   across tenants (Delhivery's own companyId is also literally "main",
#   not "delhivery" — confirms this is a Darwinbox platform convention,
#   not a per-customer value). But replaying the EXACT same headers and
#   body Playwright itself sent, byte-for-byte, still gets a Cloudflare
#   403 from plain `requests` — genuine TLS/HTTP2 fingerprint-level bot
#   detection, not a missing header. Confirms the earlier ZS Associates
#   verdict rather than overturning it: this platform structurally cannot
#   be scraped without a real browser engine, which stays out of this
#   project's runtime fetchers by design (Playwright is investigation-only
#   here). Not revisitable without that architecture decision changing.
#
# KEKA: the endpoint was actually FOUND, but could not be verified, so no
#   fetcher was written for it. Read directly out of the shipping bundle
#   (cdn.keka.com/careers/v/2026/scripts/app/app.min.js):
#       GET https://{tenant}.keka.com/api/jobs/{portalName}/active
#       portalName = <meta name="portalName"> on /careers/, and the bundle
#         itself falls back to the literal "default" when that is empty
#         (apiPortalName = ""==portalName ? "default" : portalName)
#       sibling endpoints: /api/organization/departments,
#         /api/organization/{portal}/careerportalinfo, /api/jobs/{portal}/other/{a}/{b}
#   The only live tenant found (wealthindia.keka.com) has its portal
#   DISABLED: every endpoint above 404s — including
#   /api/organization/departments, which is portal-independent, so this is
#   the tenant being off rather than the URL shape being wrong. Its
#   /careers/ page is also marked robots=noindex with an empty portalName.
#   To finish this: find a Keka tenant with a LIVE careers portal, confirm
#   the endpoint returns JSON, and only then write the fetcher — every
#   other fetcher in this project was confirmed against real data before
#   being added, and this one shouldn't be the exception.

# --- iCIMS / Jibe ---------------------------------------------------------------
# Config per company: {jobs_domain, apply_domain}. Both must be confirmed via
# browser DevTools per-company — there's no universal subdomain pattern:
#   jobs_domain: host serving GET /jobs?page=N&... JSON (Network tab, XHR filter)
#   apply_domain: host that job detail links resolve to (click a listing,
#     read the URL's host — usually careers-<slug>.icims.com)
#
# ZS uses the dedicated public /api/jobs wrapper in fetchers/zs.py.
ICIMS = [
    # Cvent (Jibe variant) — confirmed via debug/debug_cvent.py: /api/jobs
    # returns clean JSON with full descriptions; server-side location
    # filter cuts 117 global postings to 43 Gurugram/India ones. Flat job
    # objects, slug-based same-domain URLs (no apply_domain needed).
    {"company": "cvent", "jobs_domain": "careers.cvent.com", "api_path": "/api/jobs",
     "extra_params": "locations=Gurugram,,India"},
    # S&P Global — same Jibe variant as Cvent above, so it needed NO new
    # fetcher code at all, just this entry. Identified by the career page's
    # own `data-jibe-search-version` attribute in its markup, which is the
    # reliable way to spot this platform (the public URL, /jobs?page=N&
    # categories=..., looks nothing like Cvent's and gave no hint).
    #
    # WORTH REMEMBERING — this was nearly missed: an earlier sweep probed
    # careers.spglobal.com with the SuccessFactors /search/ path only, got
    # a 200 with no matching rows, and wrote it off as "live site, but not
    # a platform we support". It was actually a supported platform all
    # along, just at a different path. One negative probe against ONE
    # platform's URL shape is not evidence a site is unreachable.
    #
    # Confirmed live: 313 postings globally; country=India scopes that to
    # 69 server-side (locations=Gurugram,,India, the param Cvent uses,
    # only matches 6 here — the city spelling varies per tenant, so the
    # broader country filter is the reliable one). 24 of the 69 are NCR
    # (Gurgaon/Gurugram/Noida), and the LIST response already carries full
    # descriptions, so every row lands with real text and no detail-fetch.
    {"company": "spglobal", "jobs_domain": "careers.spglobal.com", "api_path": "/api/jobs",
     "extra_params": "country=India"},
]

# --- SmartRecruiters -------------------------------------------------------------
# Documented public no-auth Posting API — no DevTools digging needed.
# https://developers.smartrecruiters.com/docs/posting-api
# company_id = the token at the end of https://careers.smartrecruiters.com/<id>
# NOTE: tier-dependent — some SmartRecruiters customers don't have this public
# feed enabled, so an empty result can mean "disabled" not "wrong id."
#
# Config per company: {company_id, detail_fetch_india_only (optional)}.
# detail_fetch_india_only gates the per-posting detail-fetch (see
# fetchers/smartrecruiters.py) to India-located postings only, using each
# posting's own raw ISO country code (NOT core.location.is_india_or_unknown()
# — that was tried first and measured too loose here, see the fetcher's
# module docstring for why) — added specifically for Bosch below, since
# this fetcher's original design assumed small total volume (~590 postings
# across Freshworks+servicenow) and detail-fetched every posting
# unconditionally; Freshworks/servicenow don't set this flag, so their
# behavior is byte-for-byte unchanged.
SMARTRECRUITERS = [
    {"company_id": "PHONEPELIMITED"},
    {"company_id": "Freshworks"},
    {"company_id": "servicenow"},
    # Bosch — confirmed live via the real Posting API: real India postings
    # (Bangalore/Pune/Nashik) among 4,824 TOTAL postings globally — ~8x
    # this fetcher's previous combined volume. Unlike Freshworks/servicenow,
    # detail-fetching every one of those 4,824 unconditionally would be a
    # real time/rate cost for no benefit on the ~83% that aren't India-
    # relevant anyway (measured), hence detail_fetch_india_only here.
    {"company_id": "BoschGroup", "detail_fetch_india_only": True},
]

# --- Workable ----------------------------------------------------------------
# Public no-auth widget API (same one Workable's own embeddable widget uses).
# GET https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true
# slug = the token at the end of https://apply.workable.com/<slug>/
WORKABLE = []

# --- ainterviews.com -----------------------------------------------------------
# Config per company: {company, tenant}. tenant = the slug in the API path,
# found via a real network capture of the company's own careers page, not
# guessed from the company name (Lenskart's is "lenskart_ho", not "lenskart").
# See fetchers/ainterviews.py's module docstring for the full investigation.
AINTERVIEWS = [
    # Lenskart — Faridabad/Gurugram-HQ'd eyewear unicorn. Confirmed live:
    # 67 total postings, 46 NCR (69%) — nearly all Delhi-based corporate
    # roles (Product, Merchandising, Finance, Category Lead), a genuinely
    # strong NCR yield reflecting the company's real HQ location. Mostly
    # business/product roles rather than pure engineering, but real signal.
    {"company": "lenskart", "tenant": "lenskart_ho"},
]

# --- IndiaMART (klimb.io) -------------------------------------------------------
# Config per company: {company, customer_id}. See fetchers/indiamart.py's
# module docstring for the full investigation (a chatbot search endpoint
# pressed into service as a jobs-list call, since no real listing endpoint
# exists on this vendor).
INDIAMART = [
    {"company": "indiamart", "customer_id": "5dd7966c6c4d197f68105048"},
]

# --- Cosmetic display names ---------------------------------------------------
# For companies whose slug casing looks wrong via .title() (phonepe -> PhonePe).
# Anything not listed here falls back to slug.title().
DISPLAY_NAMES = {
    "deshaw": "D. E. Shaw India",
    "quadeye": "Quadeye",
    "rippling": "Rippling",
    "PHONEPELIMITED": "PhonePe",
    "towerresearchcapital": "Tower Research Capital",
    "gravitonresearchcapital": "Graviton Research Capital LLP",
    "goldman_sachs": "Goldman Sachs",  # .title() would give "Goldman_Sachs"
    "morganstanley": "Morgan Stanley",  # .title() would give "Morganstanley"
    "indiamart": "IndiaMART",  # .title() would give "Indiamart"
    "deutsche_bank": "Deutsche Bank",  # .title() would give "Deutsche_Bank"
    "standardchartered": "Standard Chartered",  # .title() would give "Standardchartered"
    "paloaltonetworks": "Palo Alto Networks",  # .title() would give "Paloaltonetworks"
    "phonepe": "PhonePe",
    "cred": "CRED",
    "roku":"Roku", "gleanwork":"Glean", "okta":"Okta", "purestorage":"Pure Storage",
    "gitlab":"GitLab", "squarepointcapital":"Squarepoint Capital",
    "quberesearchandtechnologies":"Qube Research & Technologies",
    "crowdstrike":"CrowdStrike", "broadcom":"Broadcom", "cohesity":"Cohesity",
    "postman":"Postman", "netflix":"Netflix", "automattic":"Automattic", "zerodha":"Zerodha",
    "alphagrepsecurities": "AlphaGrep",
    "nksecuritiesresearch": "NK Securities Research",
    "worldquant": "WorldQuant",
    "imc": "IMC",
    "optiverus": "Optiver",
    "mongodb": "MongoDB",
    "datadog": "Datadog",
    "amd": "AMD",
    "mediatek": "MediaTek",
    "tesco": "Tesco",
    "booking": "Booking.com",
    "juspay": "Juspay",
    "millennium": "Millennium",
    "paypal": "PayPal",
    "blackrock": "BlackRock",
    "expedia": "Expedia Group",
    "amex": "American Express",
    "jpmc": "JPMorgan Chase",
    "bcg": "Boston Consulting Group",
    "fidelity": "Fidelity International",
    "zs": "ZS Associates",
    "thoughtworks": "Thoughtworks",
    "zeta": "Zeta",
    "fractal": "Fractal Analytics",
    "Freshworks": "Freshworks",
    "servicenow": "ServiceNow",
    "salesforce": "Salesforce",
    "arcesiumllc": "Arcesium",
    "intuit": "Intuit",
    "nvidia": "NVIDIA",  # .title() would give "Nvidia" — wrong branding
    "BoschGroup": "Bosch",  # .title() on a no-space slug just capitalizes
                             # the first letter ("Boschgroup") — wrong
    "payu": "PayU",  # .title() would give "Payu" — wrong branding
    "spglobal": "S&P Global",  # .title() would give "Spglobal"
    "hp": "HP",  # .title() would give "Hp" — wrong branding
}


# --- Matching filters ----------------------------------------------------------
# Intern OR fresher/entry-level/campus/2026-27-batch hiring
INCLUDE = re.compile(
    r"\b(intern|internship|trainee|apprentice|co-?op|"
    r"graduate program|campus hire|campus drive|entry.?level|"
    r"fresher|new ?grad)\b|"
    r"\b(20)?2[67]\b", re.I  # catches "batch 2027", "2027 grads", etc.
)

EXCLUDE = re.compile(
    r"\b(senior|staff|principal|lead|manager|director|head of|"
    r"internal|international|architect|\b[3-9]\+? ?years?\b|"
    r"[3-9]-\d+ ?years?)\b", re.I
)

LOCATION = re.compile(
    r"delhi|ncr|noida|gurugram|gurgaon|ghaziabad|faridabad|gautam buddha nagar", re.I
)

# Narrow seniority filter — drops obviously senior-level titles even though
# the intern/fresher gate was removed. Checked against the title only.
#
# sr/sr\.? and mgr/mgr\.? added after a live report: "Sr. Solutions
# Architect" wasn't being caught — \bsenior\b never matches the "Sr."
# abbreviation at all, a completely different token. mgr added
# proactively as the same class of gap (common in real postings), not
# separately reported.
#
# Level indicators (II/III/IV/V, or a bare 2-9) added properly this time
# — this docstring used to CLAIM they were covered without the regex
# actually doing it; now they really are, but narrowly: matched ONLY as
# the very last token of the title (\s*$), never mid-title. That's what
# makes this safe against the real false-positive cases a looser version
# would hit:
#   - a batch year ("...- 2027 Batch"): \b[2-9]\b only ever matches a
#     single standalone digit — "2027" has no internal word boundary
#     between its digits, so this can't partial-match the leading "2"
#   - a "5B"/"4A"-style grade-code posting: "5B" has no boundary between
#     the digit and the following letter either, so \b[2-9]\b doesn't
#     match it — and even if it did, the letter suffix keeps it off the
#     end-anchored \s*$ requirement unless the title happened to end in
#     a bare digit with nothing after it
#   - a trailing team/count number that isn't a level at all: still a
#     real residual risk (can't distinguish "Data Analyst 2" the level
#     from "Data Analyst 2" a hypothetical group id from title text
#     alone) — accepted per the same "almost always" reasoning the
#     original (never-implemented) docstring already used, not newly
#     invented here
#
# CONFIRMED against every distinct title in a live db (2,868 titles):
# 80 matched via the digit/numeral clause, 79 genuinely correct (Software
# Engineer II/III, Data Engineer 2-9, etc.) and exactly 1 false positive:
# "Apprentice - 7" — not a seniority level, a program cohort number, on a
# title that's already an explicit fresher signal. Fixed by suppressing
# the digit/numeral clause (NOT the word clause — "Senior Apprentice"
# should still be caught by that one) whenever the title contains an
# intern/trainee/apprentice/fresher/etc. signal anywhere, via the
# `^(?:(?!SIGNAL).)*` prefix — the standard regex idiom for "the string
# up to this point contains none of SIGNAL", anchored at the very start
# so it actually scans the whole prefix, not just checks the current
# position (which is what a plain negative lookahead right before the
# digit would do — and would NOT have caught "Apprentice" since that
# occurs well before the digit, outside a same-position lookahead's reach).
# Level/Grade 1, or no number at all, is intentionally NOT matched —
# that's the entry tier.
_FRESHER_SIGNAL = r"intern|internship|trainee|apprentice|co-?op|fresher|entry.?level|new ?grad|graduate|new college"
# "new college" added after cross-referencing NVIDIA's own Workday
# workerSubType facet (a real "Intern"/"New College Graduate" HR
# classification, not a title guess) against title text: 160 officially
# fresher-tagged postings, only 13 (8%) had zero keyword match under the
# ORIGINAL pattern here — "new ?grad" doesn't match "New College Grad"
# (NVIDIA's own most common real phrasing), which alone accounted for
# most of that gap. Confirms this regex is already catching the vast
# majority of real fresher-tagged postings; the residual 8% (titles like
# "Firmware Architect" with zero textual signal at all) isn't worth the
# schema/fetcher-architecture cost of cross-referencing the facet
# directly — see the corresponding WORKDAY config comments for the
# per-company facet data this was checked against.
EXCLUDE_SENIOR = re.compile(
    r"\b(?:senior|sr|lead|manager|mgr|director|principal)\b\.?"
    rf"|^(?:(?!\b(?:{_FRESHER_SIGNAL})\b).)*\b(?:ii|iii|iv|v)\b\s*$"
    rf"|^(?:(?!\b(?:{_FRESHER_SIGNAL})\b).)*\b[2-9]\b\s*$",
    re.I,
)

# --- Resume relevance gate (core/matcher.py) ------------------------------------
# A deliberately simple, deterministic gate on top of the semantic+skill
# blend — added because the blend alone still gave "LLM Developer" and
# "Network Security Engineer" 60%+ match scores against a Data Analyst
# resume even after core/skills.py's taxonomy fix: their titles don't say
# anything data-analyst-shaped, and the only reason their skill overlap
# wasn't near-zero was two generic, near-universal terms (python/aws) —
# not real evidence of relevance. See core/matcher.py's apply_relevance_gate()
# for how this combines with skill overlap. Edit this list directly if
# your target role changes — this is the one place that should reflect
# what YOU are actually looking for, not a general-purpose default.
TARGET_ROLE_RE = re.compile(
    r"\bdata (analyst|analytics|engineer|scientist)\b|"
    r"\bbusiness (analyst|intelligence)\b|"
    r"\banalytics engineer\b|"
    r"\bbi (analyst|developer|engineer)\b|"
    r"\breporting analyst\b|\binsights analyst\b|"
    r"\bmachine learning engineer\b|\bml engineer\b",
    re.I,
)

RELEVANCE_FILTERS = {}

# First-party Workday boards with live India facet discovery and full descriptions.
WORKDAY_INDIA = [
    {"company":"amadeus", "tenant":"amadeus", "wd_server":"wd502", "site":"jobs"},
    {"company":"cadence", "tenant":"cadence", "wd_server":"wd1", "site":"External_Careers"},
    {"company":"analogdevices", "tenant":"analogdevices", "wd_server":"wd1", "site":"External"},
    {"company":"siemenshealthineers", "tenant":"onehealthineers", "wd_server":"wd3", "site":"SHSJB"},
    {"company":"kla", "tenant":"kla", "wd_server":"wd1", "site":"Search"},
    {"company":"broadcom", "tenant":"broadcom", "wd_server":"wd1", "site":"External_Career"},
    {"company":"crowdstrike", "tenant":"crowdstrike", "wd_server":"wd5", "site":"crowdstrikecareers"},
    {"company":"cohesity", "tenant":"cohesity", "wd_server":"wd5", "site":"Cohesity_Careers"},
    {"company":"postman", "tenant":"postman", "wd_server":"wd108", "site":"careers"},
]

DISPLAY_NAMES.update({"hrt":"Hudson River Trading", "bloomberg":"Bloomberg", "linkedin_company":"LinkedIn"})

DISPLAY_NAMES["zepto"] = "Zepto"

DISPLAY_NAMES["unitedhealthgroup"] = "UnitedHealth Group / Optum"

DISPLAY_NAMES["kla"] = "KLA"
DISPLAY_NAMES["ubs"] = "UBS"
DISPLAY_NAMES["makemytrip"] = "MakeMyTrip"
DISPLAY_NAMES["myntra"] = "Myntra"
DISPLAY_NAMES["tredence"] = "Tredence Analytics"
DISPLAY_NAMES.update({
    "sap": "SAP Labs India", "lowes": "Lowe's India",
    "nutanix": "Nutanix", "mathworks": "MathWorks", "maqsoftware": "MAQ Software",
    "micron": "Micron Technology", "commvault": "Commvault", "sigmoid": "Sigmoid Analytics",
    "cadence": "Cadence Design Systems", "analogdevices": "Analog Devices", "amadeus": "Amadeus Labs",
    "siemenshealthineers": "Siemens Healthineers", "fanaticsinc": "Fanatics Corporate",
    "fanaticscommerce": "Fanatics Commerce", "fanaticsfbg": "Fanatics Betting & Gaming",
    "fanaticscollectibles": "Fanatics Collectibles",
})


# Separate university board and student discovery outside Walmart's narrow
# "Global Tech India" search. Check all India listing pages before selecting
# Walmart student titles; fetch full descriptions only for selected titles.
STUDENT_TITLE_RE = re.compile(
    r"\b(intern(?:ship)?|apprentice(?:ship)?|student|summer analyst|"
    r"summer associate|industrial trainee|co[ -]?op)\b", re.I,
)
WORKDAY_STUDENTS = [
    {"company": "visa", "tenant": "visa", "wd_server": "wd5", "site": "Visa_Early_Careers"},
    {"company": "walmart", "tenant": "walmart", "wd_server": "wd504", "site": "WalmartExternal",
     "title_pattern": STUDENT_TITLE_RE},
]


# Explicit public India Intern search; pid is deliberately omitted because
# it selects one detail pane rather than defining the list coverage.
QUALCOMM_STUDENTS = {
    "company": "qualcomm", "host": "careers.qualcomm.com", "domain": "qualcomm.com",
    "location": "india", "sort_by": "distance", "filter_include_remote": "0",
    "filter_include_relocation": "0", "filter_seniority": "Intern",
}

DISPLAY_NAMES["netomi"] = "Netomi"

DISPLAY_NAMES["portcast"] = "Portcast"
