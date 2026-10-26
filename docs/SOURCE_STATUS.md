# Source maintenance

## 25 October 2026

These are dated checks, not guarantees of future availability or complete coverage.

| Source | Observed result | Change |
|---|---|---|
| Zerodha | The official `/api/jobs` response contained one opening with `name` as its stable slug, `job_title`, HTML description and a nullable location. | Accept the slug schema, retain full text and keep valid rows if another row is malformed. Current frontend uses accordion cards, so the careers homepage is retained when no job-specific URL is supplied. |
| Swiggy | Its official careers frontend loads `/api/jobs.json`: 202 rows, all linked to SmartRecruiters. The old MyNextHire endpoint returned HTTP 402 with an expired-subscription message. | Use the current feed and fetch identity-linked public SmartRecruiters descriptions. Live validation returned 202 jobs and 202 nonempty descriptions. Missing details/count mismatches remain partial results. |
| HRT | The configured public careers page returned HTTP 403. | Retain the explicit failure; no successful empty result or access bypass. |
| Expedia | The configured listing endpoint returned HTTP 403 with a Cloudflare challenge. | Report the HTTP status explicitly; challenge HTML is not accepted as an empty source. Keep previously fetched pages if a later page is rejected. |

The failed sources do not abort the other platform collectors. The supplied run fetched 34,557 rows and saved 42 new jobs. A connection-pool-full warning concerns connection reuse and does not itself establish a missed listing.

Live adapter verification did not write to the career database. Run career collection from the website to import the recovered sources. Existing nonempty descriptions can be refreshed on successful Swiggy/Zerodha recollection while tracking and removal state remain intact.

## 26 October 2026 — IBM

Added a dedicated India collector in `backend/fetchers/ibm.py`, registered as `ibm`. The supplied official IBM search uses the public `https://www-api.ibm.com/search/api/v2` service (`appId: careers`, `scopes: [careers2]`). The exact `field_keyword_05: India` country term is preserved. Full descriptions come from the indexed `body` field, not the short `description` snippet; fields must be requested explicitly.

Live read-only validation fetched all **1,042 reported India hits as 1,042 unique job IDs**, all with nonempty descriptions; the longest normalized description was 17,629 characters. Default relevance ordering repeated/missed jobs between pages; explicit `_id` ascending order resolved that mismatch. The adapter deduplicates requisition IDs, validates IBM detail links and India country, detects changing totals/repeated pages/search failures, and preserves partial results. Missing bodies remain explicitly incomplete rather than being replaced with snippets. No detail-page challenge, application or login endpoint is accessed.

These are all India roles, not 1,042 fresher vacancies. Use the existing role/experience filters and review eligibility. An indexed posting body can be stale or incomplete at its source. Live validation did not write to SQLite. Inventory now contains 282 company/display-name entries; IBM is removed from the unresolved-source list.

Validation: 541 unit/API tests and Python compile checks passed; release scan reported no findings.

## 26 October 2026 — Info Edge / Zwayam

Added `backend/fetchers/infoedge.py` and the fixed-operation `scripts/career/zwayam_http.ps1` transport. The official page's anonymous search is a multipart POST to `https://public.zwayam.com/jobs/search`: `filterCri` carries `paginationStartNo`, `selectedCall: sort`, `sortCriteria: {name: modifiedDate, isAscending: false}` and an empty `anyOfTheseWords`; `domain` is `careers.infoedge.com` and `companyId` is the public base64 encoding of 15578. Pagination follows actual received rows, `totalCount` and `hasMoreData`, deduplicating IDs before country filtering.

Direct page requests returned 403, and Python's HTTP clients timed out or reset. The normal PowerShell 7 Windows HTTP/2 client worked against the public APIs without cookies, authentication or challenge handling. The helper allows only this employer's public search and detail operations and has a 15-second HTTP timeout plus a 25-second Python response bound. PowerShell 7 is an optional source-specific prerequisite, documented in README; other collectors remain independent.

List `mediumDescription` fields are capped previews, and some rows contain only `JD`. Full text is fetched by a JSON POST to `https://public.zwayam.com/jobs-service/v1/jobs/careersite` using `jobId`, numeric `companyId: 15578` and the public domain. Both `longDescription` and `role` are required extraction candidates: the latter contains real engineering responsibilities/qualifications even when `longDescription` is just `JD`. Skills/experience alone never count as a full description. Declared experience bounds, including zero, are appended only after a body is found.

The site's initial count was **308**. During validation it increased to **309**. Final read-only validation retrieved **309 unique global postings**, excluded **6 foreign-only jobs**, and retained **303 explicitly India-based jobs**. **238** had substantive body text; **65** remained incomplete because the source body/detail was unavailable. For example, the Associate Vice President Engineering detail (919657) itself returned `longDescription: JD` and an empty `role`; its skills are not substituted as a description. These jobs remain in the result with empty descriptions and the source status is `partial`, not a successful complete extraction. The Lead Engineer role (682806) correctly retained its full role/qualification text. The longest normalized description was 13,136 characters.

Individual blank or closed postings do not stop later detail reads. Access restrictions stop requests immediately; repeated transport failures stop enrichment while preserving collected listings. Live validation did not write jobs to SQLite. The private audit, including incomplete posting IDs, is `runtime/artifacts/infoedge_validation.json`.

Inventory: **283 company/display-name entries**. Validation: **552 unit/API tests**, Python compile checks and release scan passed (no scan findings). Collection still starts only from the website.

## 26 October 2026 — Josh Technology Group

Added `backend/fetchers/joshtechnologygroup.py`, registered under `joshtechnologygroup`. Public list links are scoped to `.career-list__openings`; all departments are included and duplicate title/Apply links are deduplicated. Full text is taken only from the detail page's career content/openings sections. Application forms, Apply buttons and site footer boilerplate are excluded. No application actions are called.

Live read-only validation retrieved **7 roles and 7 nonempty descriptions**, including both JTGxPOD roles and all five Technical Delivery roles. Five roles explicitly state Gurgaon/Gurugram locations (one uses a separate label/value paragraph); the two Senior Front-End Developer roles omit a location, so they remain `Unknown` and the collector reports `partial`. No employer-office location is inferred for those jobs. Existing role/experience filters apply; this is not seven fresher or technical-only opportunities.

Canonical public URL slugs are used as stable IDs, including when a detail request fails and is repaired later. A canonical redirect to another job is rejected. Changed layouts, incomplete details, repeated pagination and deadlines preserve partial listings with explicit unknown fields. Validation did not write jobs to SQLite. The private report is `runtime/artifacts/jtg_validation.json`; inventory now contains **284 company/display-name entries**.

Validation: **560 unit/API tests**, Python compile checks and release scan passed (no scan findings).

## 26 October 2026 - Publicis Sapient

Added `backend/fetchers/publicissapient.py`, registered as `publicissapient`. The official India search uses the anonymous `/bin/ps-redesign/careersJobsearch` endpoint with `searchType=/search`, `lang=en`, `country=India`, and 20 rows per page. Pagination validates returned offsets, reported totals and unique posting IDs; failures preserve partial listings.

Live read-only validation retrieved **51 of 51 reported India listings, all with nonempty descriptions**. The longest normalized description was 6,076 characters. Location variants append a location suffix to the search ID while detail pages display the base requisition ID; each location-specific listing/link is retained and checked against its base requisition. These are not necessarily 51 distinct requisitions or fresher roles.

Full Job Description, Qualifications and Additional Information sections come from the embedded career detail component. JSON-LD contains a shortened preview and is not substituted for missing full text. Company boilerplate, related jobs and application controls are excluded. Missing or mismatched details remain incomplete/partial. Existing experience filters apply. Inventory now contains 285 company/display-name entries. Validation does not import into SQLite; use Start career collection in the website.

Validation: 568 unit/API tests and Python compile checks passed; release scan reported no findings.

## 26 October 2026 - HSBC

Added `backend/fetchers/hsbc.py`, registered as `hsbc`. The official portal uses an anonymous Eightfold apply-v2 API distinct from the existing PCSX adapter: `https://portal.careers.hsbc.com/api/apply/v2/jobs` with `domain=hsbc.com`, `location=India`, `start`, `num=10` and `sort_by=timestamp`. Show More Opportunities advances the offset. The adapter reads every page, deduplicates numeric posting IDs, requires an explicitly public posting and positive India location evidence, and validates canonical job URLs. Fuzzy searches, malformed schemas, changing counts, repeated pages, request failures and deadlines remain explicit failures or partial results.

Full role text comes from `/api/apply/v2/jobs/{id}?domain=hsbc.com`, specifically `job_description`, with matching ID/title/public status and India location checks. Related-job `/jobs` responses and applicant/login endpoints are not used. Empty descriptions stay empty rather than substituting department labels. Full text is retained without a 6,000-character cap.

Live read-only validation returned **159 unique India postings with 159 nonempty descriptions**, longest 15,186 characters. The server changed its reported count between 158 and 159 during pagination, so the result correctly remained partial despite having 159 unique jobs. A separate coverage check fetched all **14 Intern** and **7 Entry** filtered postings; every filtered ID was present in the full India set. No separate filtered imports are necessary. These are the source's seniority labels, not independent evidence of fresher eligibility; some Intern-labeled roles have Analyst titles and must be assessed from their descriptions.

The inventory now contains 286 company/display-name entries. Source verification did not import into career SQLite or touch reader data. Start career collection manually in the website. All 576 unit/API tests, compile checks and whitespace checks passed; the heuristic release scan reported no findings. Localhost was reloaded while both pipelines were idle.

## 26 October 2026 - transient Qualcomm failure and blocked sources

The supplied run continued into classification of 5,031 jobs after the Qualcomm students, HRT and Expedia adapters failed. Each failed platform is recorded separately; other source results continue through classification and persistence. That log line is a classification batch size, not a count of newly saved jobs or complete descriptions.

A current check of the identical Qualcomm India/Intern query succeeded: **3 listings and 3 nonempty descriptions**. This establishes current recovery, not the cause of the earlier failure. Eightfold listing failures now retain HTTP status, transport error type or invalid-JSON evidence instead of reducing every failure to `None`. Qualcomm includes the failed offset and keeps prior pages if a later request fails. The generic Eightfold collector also preserves earlier pages on such failures.

Eightfold and Expedia now retry HTTP 429 at most three attempts. They honor Retry-After seconds or HTTP dates. If the requested delay exceeds the 30-second per-wait bound, they stop and report it rather than retrying before the requested time. Missing/invalid headers use bounded backoff. HTTP 401/403 stop immediately; there is no challenge handling or identity rotation.

HRT still returned HTTP 403 with a challenge during this check. Expedia returned HTTP 403 (the supplied earlier run returned 429). Both sources remain unavailable to the collector; no recovered listings are claimed. Existing stored jobs remain intact. The changes improve transient recovery and diagnostics; they do not make access-denied sources available.

Validation: 584 unit/API tests and Python compile checks passed; heuristic release scan reported no findings. The localhost app was reloaded after the active collection finished.
