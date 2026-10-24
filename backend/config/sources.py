"""Career sources configuration. Restart the server after edits."""
import re
from .display import DISPLAY_NAMES
from .matching import STUDENT_TITLE_RE, RELEVANCE_FILTERS

SALESFORCE_RELEVANT = re.compile(
    r"\b(data analyst|analytics engineer|business intelligence|\bbi\b|"
    r"data engineer|data scientist)\b", re.I,
)


GREENHOUSE = [
    "appian", "couchbaseinc", "inmobi", "typeface",
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


LEVER = ["meesho", "cred", "paytm", "fampay", "zeta", "netomi", "portcast", "ion", "coupa"]


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


GOOGLE_CAREERS = [
    {"company": "google", "location": "India", "target_levels": ["EARLY", "INTERN_AND_APPRENTICE"]},
]


AMAZON = [
    {"loc_query": "India", "country": "IND", "industry_experience": "less_than_1_year"},
    # Student searches intentionally omit the industry-experience facet.
    {"loc_query": "India", "country": "IND", "base_query": "intern"},
    {"loc_query": "India", "country": "IND", "base_query": "apprentice"},
]


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
    {"company": "fractal", "tenant": "fractal", "wd_server": "wd1", "site": "Careers", "fetch_details": True,
     # Verified Fractal location descriptors (Oct 16): keep India secondary
     # options without labeling its foreign offices as India.
     "india_location_names": ["Bengaluru", "Chennai", "Coimbatore", "Gurgaon", "Hyderabad", "Mumbai", "Noida", "Pune"]},
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
    {"company": "nvidia", "tenant": "nvidia", "wd_server": "wd5", "site": "NVIDIAExternalCareerSite", "fetch_details": True},
    {"company": "intel", "tenant": "intel", "wd_server": "wd1", "site": "External", "fetch_details": True},
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
    {"company": "hp", "tenant": "hp", "wd_server": "wd5", "site": "ExternalCareerSite", "fetch_details": True},
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
    {"company": "cisco", "tenant": "cisco", "wd_server": "wd5", "site": "Cisco_Careers", "fetch_details": True},
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
    {"company": "ericsson", "host": "jobs.ericsson.com", "domain": "ericsson.com", "location": "India", "fetch_details": True},
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
    {"company": "qualcomm", "host": "careers.qualcomm.com", "domain": "qualcomm.com", "location": "India", "fetch_details": True},
    {"company": "morganstanley", "host": "morganstanley.eightfold.ai", "domain": "morganstanley.com", "location": "India", "fetch_details": True},
]


SUCCESSFACTORS = [
    # PayU — Gurugram-HQ'd. Confirmed live: 138 postings total, 43 of them
    # NCR (Gurgaon 41 / Noida 2) — a ~31% NCR yield, by far the highest of
    # any single company in this file. Small enough volume to safely
    # detail-fetch every India/unknown posting.
    {"company": "payu", "host": "careers.payu.in", "fetch_details": True},
    {"company": "standardchartered", "host": "jobs.standardchartered.com",
     "category_id": 9783657, "variant": "rmk", "fetch_details": True,
     "facet_filters": {"jobLocationCountry": ["India"]}},
]


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


SMARTRECRUITERS = [
    {"company_id": "Netradyne"},
    {"company_id": "PHONEPELIMITED"},
    {"company_id": "Freshworks"},
    {"company_id": "servicenow"},
    {"company_id": "BoschGroup"},
]


WORKABLE = ["amagi"]


AINTERVIEWS = [
    # Lenskart — Faridabad/Gurugram-HQ'd eyewear unicorn. Confirmed live:
    # 67 total postings, 46 NCR (69%) — nearly all Delhi-based corporate
    # roles (Product, Merchandising, Finance, Category Lead), a genuinely
    # strong NCR yield reflecting the company's real HQ location. Mostly
    # business/product roles rather than pure engineering, but real signal.
    {"company": "lenskart", "tenant": "lenskart_ho"},
]


INDIAMART = [
    {"company": "indiamart", "customer_id": "5dd7966c6c4d197f68105048"},
]


WORKDAY_INDIA = [
    {'company': 'redhat', 'tenant': 'redhat', 'wd_server': 'wd5', 'site': 'Jobs'},
    {'company': 'nxp', 'tenant': 'nxp', 'wd_server': 'wd3', 'site': 'careers'},
    {'company': 'marvell', 'tenant': 'marvell', 'wd_server': 'wd1', 'site': 'MarvellCareers'},
    {'company': 'microchip', 'tenant': 'microchiphr', 'wd_server': 'wd5', 'site': 'External'},
    {'company': 'cloudera', 'tenant': 'cloudera', 'wd_server': 'wd5', 'site': 'External_Career'},
    {'company': 'ciena', 'tenant': 'ciena', 'wd_server': 'wd5', 'site': 'Careers'},
    {'company': 'proofpoint', 'tenant': 'proofpoint', 'wd_server': 'wd5', 'site': 'ProofpointCareers'},
    {'company': 'workdaycompany', 'tenant': 'workday', 'wd_server': 'wd5', 'site': 'Workday'},
    {'company': 'silabs', 'tenant': 'silabs', 'wd_server': 'wd1', 'site': 'SiliconlabsCareers'},
    {'company': 'browserstack', 'tenant': 'browserstack', 'wd_server': 'wd3', 'site': 'External', 'verify_global_country': True},
    {'company': 'f5', 'tenant': 'ffive', 'wd_server': 'wd5', 'site': 'f5jobs', 'id_bullet_index': 1},
    {'company': 'guidewire', 'tenant': 'guidewire', 'wd_server': 'wd5', 'site': 'External'},

    {"company":"bms", "tenant":"bristolmyerssquibb", "wd_server":"wd5", "site":"BMS"},
    {"company":"geappliances", "tenant":"haier", "wd_server":"wd3", "site":"GE_Appliances"},
    {"company":"lseg", "tenant":"lseg", "wd_server":"wd3", "site":"Careers"},
    {"company":"lseg", "tenant":"lseg", "wd_server":"wd3", "site":"Graduate_Careers"},
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


WORKDAY_STUDENTS = [
    {"company": "visa", "tenant": "visa", "wd_server": "wd5", "site": "Visa_Early_Careers"},
    {"company": "walmart", "tenant": "walmart", "wd_server": "wd504", "site": "WalmartExternal",
     "title_pattern": STUDENT_TITLE_RE},
]


QUALCOMM_STUDENTS = {
    "company": "qualcomm", "host": "careers.qualcomm.com", "domain": "qualcomm.com",
    "location": "india", "sort_by": "distance", "filter_include_remote": "0",
    "filter_include_relocation": "0", "filter_seniority": "Intern",
}


DISPLAY_NAMES["netomi"] = "Netomi"


DISPLAY_NAMES["portcast"] = "Portcast"


DISPLAY_NAMES["ion"] = "ION Group"


DISPLAY_NAMES["pwc"] = "PwC India"


DISPLAY_NAMES["lseg"] = "LSEG"


DISPLAY_NAMES["ea"] = "Electronic Arts"


DISPLAY_NAMES["swissre"] = "Swiss Re"


DISPLAY_NAMES["geappliances"] = "GE Appliances"


DISPLAY_NAMES["bms"] = "Bristol Myers Squibb"


DISPLAY_NAMES.update({'redhat': 'Red Hat', 'nxp': 'NXP Semiconductors', 'marvell': 'Marvell Technology', 'microchip': 'Microchip Technology', 'cloudera': 'Cloudera', 'ciena': 'Ciena', 'proofpoint': 'Proofpoint', 'workdaycompany': 'Workday', 'silabs': 'Silicon Labs', 'f5': 'F5', 'browserstack': 'BrowserStack', 'guidewire': 'Guidewire', 'appian': 'Appian', 'couchbaseinc': 'Couchbase', 'inmobi': 'InMobi', 'typeface': 'Typeface', 'coupa': 'Coupa', 'Netradyne': 'Netradyne', 'amagi': 'Amagi', 'netapp': 'NetApp'})


GREENHOUSE.extend(['cloudflare', 'druva', 'elastic', 'harnessinc', 'highradius', 'jfrog', 'observeai', 'sumologic'])


LEVER.extend(['epifi'])


ASHBY.extend(['uipath'])


WORKABLE.extend(['innovaccer-analytics', 'tiger-analytics'])


WORKDAY_INDIA.extend([
    {'company': 'wellsfargo', 'tenant': 'wf', 'wd_server': 'wd1', 'site': 'WellsFargoJobs', 'verify_detail_country': True},
    {'company': 'accenture', 'tenant': 'accenture', 'wd_server': 'wd103', 'site': 'AccentureCareers', 'verify_detail_country': True},
    {'company': 'airbus', 'tenant': 'ag', 'wd_server': 'wd3', 'site': 'Airbus', 'verify_detail_country': True},
    {'company': 'apollo', 'tenant': 'athene', 'wd_server': 'wd5', 'site': 'Apollo_Careers', 'verify_detail_country': True},
    {'company': 'bakerhughes', 'tenant': 'bakerhughes', 'wd_server': 'wd5', 'site': 'BakerHughes', 'verify_detail_country': True, 'verify_global_country': True},
    {'company': 'blackstone', 'tenant': 'blackstone', 'wd_server': 'wd1', 'site': 'Blackstone_Careers', 'verify_detail_country': True, 'verify_global_country': True},
    {'company': 'boeing', 'tenant': 'boeing', 'wd_server': 'wd1', 'site': 'EXTERNAL_CAREERS', 'verify_detail_country': True},
    {'company': 'broadridge', 'tenant': 'broadridge', 'wd_server': 'wd5', 'site': 'Careers', 'verify_detail_country': True},
    {'company': 'capitalone', 'tenant': 'capitalone', 'wd_server': 'wd12', 'site': 'Capital_One', 'verify_detail_country': True, 'india_facet_pattern': '^Bangalore,\\s*IN$'},
    {'company': 'citi', 'tenant': 'citi', 'wd_server': 'wd5', 'site': '2', 'verify_detail_country': True},
    {'company': 'dbs', 'tenant': 'dbs', 'wd_server': 'wd3', 'site': 'DBS_Careers', 'verify_detail_country': True},
    {'company': 'factset', 'tenant': 'factset', 'wd_server': 'wd108', 'site': 'FactSetCareers', 'verify_detail_country': True, 'verify_global_country': True},
    {'company': 'fidelityinvestments', 'tenant': 'fmr', 'wd_server': 'wd1', 'site': 'FidelityCareers', 'verify_detail_country': True},
    {'company': 'fis', 'tenant': 'fis', 'wd_server': 'wd5', 'site': 'SearchJobs', 'verify_detail_country': True, 'verify_global_country': True},
    {'company': 'gartner', 'tenant': 'gartner', 'wd_server': 'wd5', 'site': 'EXT', 'verify_detail_country': True},
    {'company': 'geaerospace', 'tenant': 'geaerospace', 'wd_server': 'wd5', 'site': 'GE_ExternalSite', 'verify_detail_country': True, 'verify_global_country': True},
    {'company': 'iqvia', 'tenant': 'iqvia', 'wd_server': 'wd1', 'site': 'IQVIA', 'verify_detail_country': True},
    {'company': 'morningstar', 'tenant': 'morningstar', 'wd_server': 'wd5', 'site': 'Americas', 'verify_detail_country': True},
    {'company': 'nasdaq', 'tenant': 'nasdaq', 'wd_server': 'wd1', 'site': 'Global_External_Site', 'verify_detail_country': True},
    {'company': 'natwest', 'tenant': 'rbs', 'wd_server': 'wd3', 'site': 'RBS', 'verify_detail_country': True, 'id_bullet_index': 1},
    {'company': 'northerntrust', 'tenant': 'ntrs', 'wd_server': 'wd1', 'site': 'northerntrust', 'verify_detail_country': True},
    {'company': 'quantiphi', 'tenant': 'quantiphi', 'wd_server': 'wd1', 'site': 'Careers_at_Quantiphi', 'verify_detail_country': True, 'verify_global_country': True},
    {'company': 'shell', 'tenant': 'shell', 'wd_server': 'wd3', 'site': 'ShellCareers', 'verify_detail_country': True},
    {'company': 'statestreet', 'tenant': 'statestreet', 'wd_server': 'wd1', 'site': 'Global', 'verify_detail_country': True},
    {'company': 'thomsonreuters', 'tenant': 'thomsonreuters', 'wd_server': 'wd5', 'site': 'External_Career_Site', 'verify_detail_country': True, 'id_bullet_index': 2},
    {'company': 'thoughtspot', 'tenant': 'thoughtspot', 'wd_server': 'wd5', 'site': 'careers', 'verify_global_country': True},
    {'company': 'uniphore', 'tenant': 'uniphore', 'wd_server': 'wd503', 'site': 'Uniphore', 'verify_detail_country': True},
])


EMPLOYER_PORTALS = [
    {'company': 'upstox', 'kind': 'upstox'},
    {'company': 'hasura', 'kind': 'gem', 'board': 'promptql', 'expected_team': 'PromptQL'},
    {'company': 'c5i', 'kind': 'c5i'},
    {'company': 'mathco', 'kind': 'peoplestrong', 'host': 'mathco-careers.peoplestrong.com'},
    {'company': 'acko', 'kind': 'kula', 'account': 'acko'},
    {'company': 'akamai', 'kind': 'oracle', 'base_url': 'https://fa-extu-saasfaprod1.fa.ocs.oraclecloud.com', 'site': 'CX_1'},
    {'company': 'anz', 'kind': 'successfactors', 'host': 'careers.anz.com'},
    {'company': 'bny', 'kind': 'oracle', 'base_url': 'https://eofe.fa.us2.oraclecloud.com', 'site': 'BNY-Careers'},
    {'company': 'cashfree', 'kind': 'kula', 'account': 'cashfree'},
    {'company': 'clevertap', 'kind': 'kula', 'account': 'clevertap'},
    {'company': 'eightfoldai', 'kind': 'pcsx', 'host': 'app.eightfold.ai', 'domain': 'volkscience.com'},
    {'company': 'evalueserve', 'kind': 'darwinbox', 'host': 'lighthouse.darwinbox.com'},
    {'company': 'exxonmobil', 'kind': 'successfactors', 'host': 'jobs.exxonmobil.com'},
    {'company': 'honeywell', 'kind': 'oracle', 'base_url': 'https://ibqbjb.fa.ocs.oraclecloud.com', 'site': 'CX_1'},
    {'company': 'icertis', 'kind': 'oracle', 'base_url': 'https://iaaviz.fa.ocs.oraclecloud.com', 'site': 'Jobs-at-Icertis'},
    {'company': 'jupiter', 'kind': 'keka', 'host': 'jupiter.keka.com'},
    {'company': 'latentview', 'kind': 'darwinbox', 'host': 'latentview.darwinbox.in'},
    {'company': 'moengage', 'kind': 'trakstar', 'host': 'moengage.hire.trakstar.com'},
    {'company': 'perfios', 'kind': 'darwinbox', 'host': 'perfios.darwinbox.in'},
    {'company': 'porter', 'kind': 'darwinbox', 'host': 'porter.darwinbox.in'},
    {'company': 'slice', 'kind': 'kula', 'account': 'slice'},
    {'company': 'spinny', 'kind': 'darwinbox', 'host': 'spinzone.darwinbox.in'},
    {'company': 'whatfix', 'kind': 'trakstar', 'host': 'whatfix101.hire.trakstar.com'},
    {'company': 'wingify', 'kind': 'keka', 'host': 'wingify.keka.com'},
]


DISPLAY_NAMES.update({
    'upstox': 'Upstox',
    'hasura': 'PromptQL (Hasura)',
    'c5i': 'C5i',
    'mathco': 'MathCo',
    'accenture': 'Accenture',
    'acko': 'Acko',
    'akamai': 'Akamai Technologies',
    'evalueserve': 'Evalueserve',
    'wellsfargo': 'Wells Fargo',
    'airbus': 'Airbus',
    'anz': 'ANZ',
    'apollo': 'Apollo Global Management',
    'bakerhughes': 'Baker Hughes',
    'blackstone': 'Blackstone',
    'bny': 'BNY',
    'boeing': 'Boeing',
    'broadridge': 'Broadridge',
    'capitalone': 'Capital One',
    'cashfree': 'Cashfree Payments',
    'citi': 'Citi',
    'clevertap': 'CleverTap',
    'cloudflare': 'Cloudflare',
    'dbs': 'DBS Bank',
    'druva': 'Druva',
    'eightfoldai': 'Eightfold AI',
    'elastic': 'Elastic',
    'epifi': 'Fi Money',
    'exxonmobil': 'ExxonMobil',
    'factset': 'FactSet',
    'fidelityinvestments': 'Fidelity Investments',
    'fis': 'FIS',
    'gartner': 'Gartner',
    'geaerospace': 'GE Aerospace',
    'harnessinc': 'Harness',
    'highradius': 'HighRadius',
    'honeywell': 'Honeywell',
    'icertis': 'Icertis',
    'innovaccer-analytics': 'Innovaccer',
    'iqvia': 'IQVIA',
    'jfrog': 'JFrog',
    'jupiter': 'Jupiter Money',
    'latentview': 'LatentView Analytics',
    'moengage': 'MoEngage',
    'morningstar': 'Morningstar',
    'nasdaq': 'Nasdaq',
    'natwest': 'NatWest Group',
    'northerntrust': 'Northern Trust',
    'observeai': 'Observe.AI',
    'perfios': 'Perfios',
    'porter': 'Porter',
    'quantiphi': 'Quantiphi',
    'shell': 'Shell',
    'slice': 'Slice',
    'spinny': 'Spinny',
    'statestreet': 'State Street',
    'sumologic': 'Sumo Logic',
    'thomsonreuters': 'Thomson Reuters',
    'thoughtspot': 'ThoughtSpot',
    'tiger-analytics': 'Tiger Analytics',
    'uipath': 'UiPath',
    'uniphore': 'Uniphore',
    'whatfix': 'Whatfix',
    'wingify': 'Wingify',
})

