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
