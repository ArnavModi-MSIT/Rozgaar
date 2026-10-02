# Career source verification — 2 October 2026

These are live request results, not permanent guarantees or fresher eligibility counts.
The checks did not populate SQLite. Run `python run.py` to save postings.

| Company | Result | India roles | Description coverage | Link check |
| --- | --- | ---: | --- | --- |
| Databricks | Existing Greenhouse feed: 873 global postings | 94 | 94 descriptions | One India branded detail link returned 200 |
| Rubrik | Existing Greenhouse feed: 129 global postings | 21 | 21 descriptions | Branded detail returned 403; Greenhouse detail redirects to the same branded page |
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
