# Source maintenance

## 27 October 2026 - HRT and Expedia disabled

At the user's request, removed HRT and Expedia from active platform registration and imports. HRT's HTTP 403 challenge and Expedia's HTTP 403/earlier 429 are recorded in `DISABLED_CAREER_SOURCES` and the generated inventory's Disabled sources section. They will not be requested in subsequent collections. The active inventory now contains 292 company/display-name entries; the two disabled sources are listed separately. Their adapters and regression tests remain available for future maintenance, while saved jobs, tracking/removal state, snapshots and run history are preserved. Earlier source-specific notes below are historical and do not imply either source is still active.

## 27 October 2026 - Expedia India scope

Changed Expedia to the supplied India-filtered search. Pagination now sends `filter[country]=India` on every `/calc-results/` request, and the Referer is the filtered search. An independent result guard accepts only India-prefixed location labels, including the site's `India - Bangalore` and `India - Haryāna - Gurgaon` format. Duplicate detection still tracks all returned cards so a foreign-only page cannot accidentally terminate pagination early.

The public search result showed 11 India positions. Live requests from the collector environment to both the filtered search and first filtered pagination request returned HTTP 403, so no successful retrieval of those 11 is claimed. The existing blocked-source failure and bounded 429 retry policy remain in effect. Descriptions are still listing team metadata, not full job bodies. Fixtures verify the query and exclusion of a United States/Indiana card; downstream live pagination remains unverified while blocked. Existing jobs and snapshots are preserved.

## 27 October 2026 - HRT Mumbai scope

Changed HRT's source URL to the user-supplied `/careers/?locations=mumbai%2C`. The same location query is included in the existing listing request, with an independent Mumbai-only result guard. Mumbai labels are normalized to Mumbai, India. Other cities are excluded; no one-job cap is imposed on future valid Mumbai results.

The supplied screenshot shows one Security Engineer posting. A live request to this exact filtered URL still returned HTTP 403 with a challenge, so the collector remains blocked before listing retrieval. No live posting or full-description success is claimed. The downstream request/filter behavior is covered by fixtures but remains unverified against the blocked live service. Listing descriptions remain explicitly marked as summaries. Existing saved jobs and exports are unchanged; the change does not bypass access controls.

Validation: all 627 unit/API tests, Python compile and whitespace checks passed. The active career collection was not interrupted or restarted.

## 27 October 2026 - Rocketlane India

Registered Rocketlane in EMPLOYER_PORTALS using the existing Kula adapter with account `rocketlane`. The official board delivers the complete job array and full descriptions in its React Flight stream. The adapter decodes the delivered data without executing scripts, validates account identity, excludes confidential/unlisted jobs and requires India country metadata in office records. UTF-8 text references resolve by byte length; descriptions have no extraction length cap. No pagination or application requests are needed for this feed.

Live read-only validation returned **31 unique India listings with 31 nonempty descriptions**, longest normalized body 8,681 characters. Foreign-only jobs are excluded; multinational jobs retain India offices. Separate IDs remain separate even with repeated titles. Inventory now contains 293 company/display-name entries. Existing role/experience filters apply; fresher eligibility and salary are not established. Verification did not import SQLite jobs or change snapshots; start career collection manually to import.

Validation: all 624 unit/API tests, Python compile and whitespace checks passed; heuristic release scan reported no findings. Localhost was reloaded while idle.

## 27 October 2026 - Teradata India

Added `backend/fetchers/teradata.py`, registered as `teradata`. The current official careers site uses GR8 People. The public `/graphql` searchJobPostings query filters location by address India, returning public posting keys, titles, full descriptionHTML, primary/additional place names, totalCount and cursor pagination. No account or application requests are used.

Live validation returned **85 unique India postings with 85 nonempty descriptions**, longest normalized body 9,262 characters, across five cursor pages. Returned place names must positively identify India. Full text is normalized without a length cap. Official `/jobs/{key}/{title-slug}` links were verified against a live detail page. Failed requests, GraphQL errors, invalid schemas, changing/mismatched totals, missing/repeated cursors, deadlines and empty descriptions remain explicit partial/failure evidence; prior pages are retained.

Inventory now contains 292 company/display-name entries. This replaces the unresolved Workday lead. Existing role and experience filters apply. Verification did not import jobs into SQLite or rewrite exports; start career collection manually to import.

Validation: all 624 unit/API tests, Python compile and whitespace checks passed. Heuristic release scan reported no findings.

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

## 26 October 2026 - Medtronic malformed rows and EXL experience

Four legacy Medtronic rows in local storage had blank titles and a generic Workday homepage URL (three were reported in the reviewed export). Workday now rejects cards without a nonblank title and a `/job/` detail path, reporting malformed rows as partial-source evidence. The API excludes legacy blank-title rows from the career pool and subsequent exports without deleting them, changing tracking/removal state or rewriting old snapshots.

EXL qualification bodies can state education followed by `5-8 years`, `8+ years` or `6-12 years` without the word experience. Experience requirements now recognize numeric ranges/plus counts after education context and exact role-title headings in the description. Plural `roles`/`positions` in clauses such as `8+ years in data engineering/ETL roles` are also recognized. Explicit preferences remain separate; months, degree/course durations and company-age statements do not become year requirements. The lower endpoint of a range is used. Existing rows are reparsed on API load, so no recollection or SQLite rewrite is required; unknown requirements remain visible.

Validation: all 590 unit/API tests passed. A read-only scan found 113 stored EXL records containing the reported year patterns; none remained at one year or unknown after parsing. The reloaded localhost API returned zero blank-title Medtronic rows. Python compile and whitespace checks passed. Existing exported snapshots are unchanged; download a new JSON for corrected selection.

## 27 October 2026 - Siemens Digital Industries Software

Added `backend/fetchers/siemenssoftware.py`, separate from Siemens Healthineers. The public site uses DE Jobs search: POST `https://prod-search-api.jobsyn.org/api/v1/solr/search`, X-Origin `jobs.sw.siemens.com`, data `location=india`, page numbers and `num_items=10`. The public Nuxt site configuration supplies employer IDs 38591 and 38526. Supplying that employer configuration is essential: the unscoped service returns unrelated employers. Every saved row must match an allowed employer ID and `country_exact=India`.

Full descriptions come from the site's documented-in-frontend public detail URL `https://microsites.dejobs.org/jobs-sw-siemens-com/data/{GUID}.json`, using `html_description`. Job GUID, requisition ID, title, employer and country are checked; expired detail records and unavailable text stay partial. Posting GUIDs are the stable storage IDs because different location listings can share a requisition number. Underscores in published title slugs are retained. Job links use the official `/{location}/{title}/{GUID}/job/` route. Search snippets are not substituted for missing full detail text.

Pagination follows the reported page/end state, detects duplicate pages and changing totals, preserves partial rows and observes the collector deadline. No application, login or browser state is accessed. Inventory now contains 287 company/display-name entries. This is an India source, not a guarantee of fresher eligibility or an 8 LPA offer; existing role and experience filters apply. Live verification does not import jobs into SQLite; start career collection manually.

Live validation: 61 of 61 unique India postings, all 61 with nonempty full descriptions; longest 11,199 characters. All 597 unit/API tests and compile/whitespace checks passed. Heuristic release scan reported no findings.

## 27 October 2026 - Barracuda Bangalore

Added `backend/fetchers/barracuda.py`, registered as `barracuda`. The supplied official careers page loads its full public JSON feed from the CareersRoom component's `data-panel-endpoint`, then filters in-browser. The collector discovers that same same-origin `/content/barracuda-corp/us/en/company/careers/...careers.json` endpoint and filters exactly `Bangalore, India`, preserving the supplied URL's location scope. There is no pagination: the single feed contains all 52 current global jobs.

Live read-only validation retrieved **18 unique Bangalore listings, all 18 with nonempty descriptions**, longest 10,828 normalized characters. Full HTML description text is included directly in the feed. Only external posting IDs, nonblank titles, exact Bangalore locations, identity-matched public Jobvite detail links and description text enter the normalized records. Custom fields, application links and other metadata are not copied. No application, account or browser state is accessed. Duplicate/malformed rows and missing text produce partial results; invalid schemas cannot become a successful empty feed.

Inventory now contains 288 company/display-name entries. Barracuda is removed from unresolved sources. Existing role and experience filters apply; these are not necessarily fresher openings. Verification did not import into SQLite or alter snapshots. Start career collection from the website to import.

Validation: 603 unit/API tests, Python compile and whitespace checks passed; heuristic release scan reported no findings. Localhost was reloaded while both pipelines were idle.

## 27 October 2026 - Axtria India and FDE India

Added `backend/fetchers/axtria.py`, registered as `axtria`. The supplied official page exposes static cards under `#fde-career`, covering India, FDE India, US and global FDE tabs. The collector retains cards explicitly marked `data-india-job=true` or with an India location, excludes foreign/global cards, and deduplicates source IDs. Hyderabad-only cards gain India from the explicit India-tab marker. The page currently presents all cards at once; no pagination is needed.

SuccessFactors details are read only from the employer's official linked host and company (`career10.successfactors.com`, `axtriaindiP`). The collector uses the exact published public/share-view links, without guessing tokens or using an account. The page title must identify the requisition and `.joqReqDescription .externalPosting` must contain a body. Form fields and application controls are excluded; text has no extraction length cap. LinkedIn-only cards are retained with empty descriptions, without visiting LinkedIn or accessing browser state.

Live validation returned **17 unique India/FDE India listings, 10 with nonempty descriptions and 7 unavailable**; longest normalized retrieved body 4,543 characters. Two missing descriptions are LinkedIn-only. Five SuccessFactors pages remained unavailable, including the FDE India listing; their ordinary public views state the job cannot be viewed and may have been removed or closed. The exact published share links did not recover those bodies. Do not infer eligibility from missing text or mark those jobs rejected. The source correctly reports partial status and preserves incomplete cards.

Inventory now contains 289 company/display-name entries. Existing experience/location filters apply; these listings are not verified fresher roles or salary offers. Live verification did not import SQLite data, alter exports or submit applications. Start career collection manually to import.

Validation: 609 unit/API tests, Python compile and whitespace checks passed. Heuristic release scan reported no findings. Localhost was reloaded while both pipelines were idle.

## 27 October 2026 - BMC Software India

Added `backend/fetchers/bmcsoftware.py`, registered as `bmcsoftware`. The official Avature site is `jobs.bmc.com`, distinct from the previously rejected hospital Workday tenant. The supplied search preserves India location field `16484=[9406]`, format 5516, filter mode 1 and six records per page. The collector follows the actual Next link, validates that scope and increasing jobOffset, deduplicates numeric job IDs and checks the reported total. Malformed pages, changing totals, repeated pages, deadline stops and missing descriptions remain partial/failure evidence.

Every listing needs a title, India location and a same-host `/Careers/JobDetail/.../{ID}` link. Details must have the same Job ID and Country India in Basic Information. Full text comes from the Description and Requirements content section, retaining qualifications without an extraction cap; navigation, forms and hidden fields are excluded. All collection is public HTTP; account and application operations are not used. Inventory now contains 290 company/display-name entries. Existing role/experience filters apply; configured jobs are not necessarily fresher roles. Live verification does not import SQLite jobs or change snapshots.

Live validation: all 21 reported India postings retrieved as 21 unique IDs across four pages, all with nonempty descriptions; longest 7,363 normalized characters. All 615 unit/API tests, compile and whitespace checks passed; heuristic release scan reported no findings. Localhost was reloaded while idle.

## 27 October 2026 - NCR Voyix APAC India

Registered `ncrvoyix` in the existing Workday inventory (`backend/config/sources.py`): tenant `ncr`, server `wd1`, site `ext_apac`, India applied facet `Location_Country=c4f78be1a8f14da0ab49ce1162348a5e`, and full detail fetching enabled. The supplied APAC site resolves the previous `ext_non_us` board's missing India scope. Detail descriptions identify the company as NCR Voyix; this does not establish coverage of NCR Atleos or other employers.

Live read-only validation returned **27 unique India jobs with 27 nonempty descriptions**, across offsets 0 and 20; longest normalized description 7,846 characters. Workday jobReqId is checked against each listing, and country metadata normalizes India locations. All existing malformed-card, pagination, deadline and partial-description safeguards apply. No separate adapter, application request, browser profile or account is needed. Inventory now contains 291 company/display-name entries. Existing role/experience filters apply; these are not necessarily fresher roles. Verification did not import into SQLite or change existing exports. Start career collection manually to import.

Validation: 618 unit/API tests, Python compile and whitespace checks passed; heuristic release scan reported no findings. Localhost was reloaded while both pipelines were idle.

## 27 October 2026 - Sprinto India

Registered the case-sensitive `Sprinto` Lever account in LEVER with display name Sprinto. Lowercase `sprinto` returned 404; the supplied uppercase board and matching public postings API returned 36 jobs after an initial API timeout. The existing Lever adapter is used, with explicit positive India scoping for this account. Country and secondary-location metadata preserve India roles while excluding foreign-only and unknown generic remote jobs. Full text includes introduction, all headed lists and additional content without a cap.

The live 36-record API response was processed by the adapter: **32 unique India listings, all 32 with nonempty descriptions**, longest 8,798 normalized characters. Four foreign-only roles were excluded. This check used the captured live API response to validate parsing without another network request. No job application, account, browser or SQLite mutation occurred. The collector uses existing bounded HTTP retries and reports failed requests rather than a successful empty board. Inventory now contains 294 company/display-name entries. Existing role/experience filters apply; junior eligibility and salary remain posting-specific. Start career collection manually to import.

Validation: 626 unit/API tests, Python compile and whitespace checks passed; heuristic release scan reported no findings. Localhost was reloaded while idle.

Validation: 628 unit/API tests, Python compile and whitespace checks passed. Localhost was reloaded after collection finished.

Validation: 629 unit/API tests, Python compile and whitespace checks passed; heuristic release scan reported no findings. Localhost was reloaded while idle.

## 28 October 2026: local transport setup

Info Edge now also discovers PowerShell 7 in `runtime/tools/powershell/`, independent of launcher PATH. Standard and SmartRecruiters HTTP pools block at their worker capacity instead of discarding excess returned connections. A BlackRock HTTP 504 remains a remote request failure; exhausted description retries retain an explicit missing description and partial source status.
