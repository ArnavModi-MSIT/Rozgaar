# Career source verification — 2 October 2026

These are live request results, not permanent guarantees or fresher eligibility counts.
The checks did not populate SQLite. Run `python run.py` to save postings.

| Company | Result | India roles | Description coverage | Link check |
| --- | --- | ---: | --- | --- |
| Databricks | Existing Greenhouse feed: 873 global postings | 94 | 94 descriptions | One India branded detail link returned 200 |
| Rubrik | Existing Greenhouse feed: 129 global postings, India office metadata normalized | 32 | 32 descriptions | Branded detail returned 403; Greenhouse detail redirects to the same branded page |
| Uber | Existing India feed: partial, 19 unique of 20 reported | 19 | 19 descriptions | One detail link returned 200 |
| Goldman Sachs | Existing GraphQL feed: 774 global postings | 122 | Division/function/skills summaries, not full job descriptions | One detail link returned 200 |
| JPMorgan Chase | Existing Oracle India location facet | 322 | 322 descriptions | One Oracle detail link returned 200 |
| Rippling | Newly connected public careers search | 79 | 79 full descriptions | One public ATS detail link returned 200 |
| D. E. Shaw India | Newly connected embedded careers payload | 72 | 72 descriptions with responsibility/qualification sections | One official detail link returned 200 |
| Quadeye | Newly connected official Zoho-backed endpoint: 25 global records | 13 | 13 India descriptions | One official detail link returned 200 |
| LinkedIn | Removed at user request | — | — | Remains excluded |

D. E. Shaw exposed 78 entries before filtering out exploratory/general applications and inactive entries. Rippling search entries can repeat a job across locations; the adapter deduplicates jobId and combines India locations. Its frontend-provided public search configuration is discovered each run, kept in memory, and used only for search queries. It is not written to files.

Quadeye's response contains additional recruiter and internal tracking metadata. The adapter keeps only the common job fields and does not store that metadata. Its public frontend displays the returned job records directly, so the collector follows that surface rather than guessing a filter from vendor flags.

Uber's reported-total mismatch is retained as partial health. Rubrik's 403 is a detail-page access limitation from this environment; its listing API and descriptions still work. Goldman descriptions remain summaries, which can reduce matching quality.

Official career pages:
- Rippling: https://www.rippling.com/careers/open-roles
- D. E. Shaw India: https://www.deshawindia.com/careers
- Quadeye: https://www.quadeye.com/jobs

Rubrik department coverage verified: Engineering has 8 India roles and Information Technology & Services has 3. The complete feed already includes all those postings. Office metadata normalization increases the recognized India total from 21 to 32 across all departments without creating duplicate collectors.

## Arcesium, Intuit and existing company check (2026-10-02)

| Company | Recognized India listings | Description check |
| --- | ---: | --- |
| Arcesium | 24 (49 global) | 24 full descriptions; newly connected official Greenhouse board |
| Intuit | 26 | All 26, both country-facet pages; new TalentBrew collector status ok |
| Salesforce | 45 (1514 global) | All 45 full descriptions after enabling details |
| Adobe | 80 (530 global) | 80 description teasers, not full JDs |
| Walmart Global Tech | 226 (403 search results) | Full-description fetching enabled; 220 India descriptions directly counted before resolving ambiguous locations. Detail country metadata resolved all remaining records: 226 India, 177 US, zero unknown. |
| ServiceNow | 76 (711 global) | All 76 full descriptions |
| Palo Alto Networks | 152 (1505 global) | All 152 full descriptions after enabling details |
| Snowflake | 13 (345 global) | All 13 full descriptions |

Counts are a live snapshot, not a guarantee of future availability. Existing Workday fetchers return plain lists and do not expose per-company completeness status. Unknown locations can pass the current India-or-unknown filter. No database history was deleted. Offline verification: 72 tests and Python compileall passed.

## PayPal, CRED, Groww, Meesho, BlackRock, Morgan Stanley, Expedia (2026-10-02)

| Company | India jobs | Live result |
| --- | ---: | --- |
| PayPal | 10 | New Workday India location facets; all 10 full descriptions, status ok. Official PayPal India site links Eightfold, which also reports 10 India roles. |
| CRED | 8 | Existing Lever board; all 8 descriptions; Bengaluru/Hyderabad labels now normalized to India. |
| Groww | 7 | Existing Greenhouse board; all 7 India jobs have descriptions. |
| Meesho | 57 | Existing Lever board; all 57 descriptions; confirmed India city/state labels normalized. |
| BlackRock | 39 | New official India TalentBrew country facet; all four pages and 39 full descriptions, status ok. |
| Morgan Stanley | 118 | Existing Eightfold India search; department summaries only. |
| Expedia Group | 4 in final partial run | Intermittent HTTP 403: initial check returned 162 global / 27 India; final check returned 100 global / 4 India and failed page 5. Completeness is unverified; team summaries only. |

Expedia failures now propagate to source health instead of silently appearing as successful empty or truncated collections. Counts are current snapshots, not guaranteed stable totals. Offline checks: 77 tests and compileall passed. Database history remains untouched.

## Fifteen additional company sources (2026-10-02)

| Company | Confirmed India jobs | Live verification |
| --- | ---: | --- |
| AlphaGrep | 7 | 15 raw Greenhouse rows; full descriptions; ambiguous multiple-location records omitted |
| NK Securities Research | 12 | 14 raw Greenhouse rows; full descriptions |
| WorldQuant | 8 | 96 raw Greenhouse rows; city-only India locations normalized |
| IMC | 16 | 167 raw Greenhouse rows, includes mixed international/India locations |
| Optiver | 4 | 168 raw rows on `optiverus`; `optiver` is an empty obsolete board |
| Confluent | 1 | 17 raw Ashby rows; full description. Branded portal returned 429; broader portal coverage unverified |
| MongoDB | 83 | 393 raw Greenhouse rows; India city combinations normalized |
| Datadog | 8 | 440 raw Greenhouse rows; full descriptions |
| Juspay | 0 | Official main page explicitly says no global openings; successful empty result. Indexed detail URLs exist but are not linked from that current page and were not assumed active |
| AMD | 200 | Public India API pagination status ok; all descriptions; country metadata normalized |
| MediaTek | 17 | All 617 global records across 7 pages checked; 17 India office records with descriptions, status ok |
| Target | 67 | All five India search pages and full descriptions, status ok |
| Tesco | 25 | All three official India search pages and full descriptions, status ok |
| Booking.com | 24 | Public India API status ok, full descriptions; sample public job link HTTP 200 |
| Millennium | 39 | Public legacy Eightfold India search status ok; department summaries only |

Final tests: 86 offline unittest tests passed and Python compileall passed. Primary branded pages can be blocked while their linked public ATS listings work. Full descriptions remain subject to the adapters' documented character limits. No production collection or database cleanup was performed during these checks.


## Requested company audit (2026-10-02)

See [COMPANY_SOURCE_AUDIT.md](COMPANY_SOURCE_AUDIT.md) for all 75 companies and live results; [COMPANY_SOURCES.json](COMPANY_SOURCES.json) defines the audit manifest. Run `python scripts/audit_company_sources.py` to refresh JSON without writing jobs to SQLite.

New India-scoped Workday collectors discover country/location facets for Broadcom, CrowdStrike, Cohesity and Postman, paginate and fetch descriptions. New Greenhouse boards cover Roku, Glean, Okta, Pure Storage, GitLab, Squarepoint and QRT. Dedicated collectors cover Netflix, Bloomberg, HRT, Automattic and Zerodha. LinkedIn employer-only guest search is explicitly partial with missing descriptions and no reliable total; the general LinkedIn job-board source remains removed. Swiggy and ZS location normalization now preserves recognized India locations.

Four companies have no verified working collector: Indeed employer, Zepto, Citadel Securities and Zomato. Empty feeds, inaccessible feeds and partial results remain distinct. Automattic remote eligibility needs individual review; Zerodha nonempty schema must be verified when vacancies appear.
