# Source maintenance: 25 October 2026

These are dated checks, not guarantees of future availability or complete coverage.

| Source | Observed result | Change |
|---|---|---|
| Zerodha | The official `/api/jobs` response contained one opening with `name` as its stable slug, `job_title`, HTML description and a nullable location. | Accept the slug schema, retain full text and keep valid rows if another row is malformed. Current frontend uses accordion cards, so the careers homepage is retained when no job-specific URL is supplied. |
| Swiggy | Its official careers frontend loads `/api/jobs.json`: 202 rows, all linked to SmartRecruiters. The old MyNextHire endpoint returned HTTP 402 with an expired-subscription message. | Use the current feed and fetch identity-linked public SmartRecruiters descriptions. Live validation returned 202 jobs and 202 nonempty descriptions. Missing details/count mismatches remain partial results. |
| HRT | The configured public careers page returned HTTP 403. | Retain the explicit failure; no successful empty result or access bypass. |
| Expedia | The configured listing endpoint returned HTTP 403 with a Cloudflare challenge. | Report the HTTP status explicitly; challenge HTML is not accepted as an empty source. Keep previously fetched pages if a later page is rejected. |

The failed sources do not abort the other platform collectors. The supplied run fetched 34,557 rows and saved 42 new jobs. A connection-pool-full warning concerns connection reuse and does not itself establish a missed listing.

Live adapter verification did not write to the career database. Run career collection from the website to import the recovered sources. Existing nonempty descriptions can be refreshed on successful Swiggy/Zerodha recollection while tracking and removal state remain intact.
