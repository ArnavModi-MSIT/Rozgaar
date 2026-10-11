# Job Intel

The [additional 20-company audit](docs/COMPANY_BATCH_20.md) records seventeen
newly connected employers, live coverage counts, and three pending sources.

## Local folder layout

On this Windows workspace, the outer folder contains only the two CMD launchers, `app/`, and `.venv/`. Application files and documentation are inside `app/`. Use **Open Job Intel.cmd** for saved jobs only, or **Start Job Intel.cmd** for the site plus collection. The launchers also support a normal flat Git clone.

For terminal commands in the organized workspace, first run `cd app`, then activate `..\.venv\Scripts\Activate.ps1`. Without activation: `..\.venv\Scripts\python.exe run.py` or `..\.venv\Scripts\python.exe stats.py`. Keep `.venv` at its original location; Windows entrypoints may contain absolute paths. `..\.venv\Scripts\python.exe start.py --check` checks paths without starting services. If a launcher reports an older backend, close that backend's console with Ctrl+C, then launch again.

## Project overview

A local job discovery prototype for students and early career applicants in India. It collects public job listings from supported career sites, stores them in SQLite, and ranks them against an uploaded resume.

## What works

- Platform-specific collectors for career sites and job boards, with a shared job format.
- Location filtering, duplicate detection, last-observed dates, job classification, skill extraction, and experience extraction.
- Collection and the API exclude locations confidently outside India, including US state names such as `California` and clear city-only cases such as `San Francisco`. Unresolved locations stay visible for review; older foreign rows remain in SQLite but are hidden by the API.
- PDF, DOCX, and TXT resume upload (5 MB limit). Matching combines `all-MiniLM-L6-v2` semantic similarity with explicit skill overlap. Resume skills can be corrected in the React sidebar.
- React interface backed by FastAPI, using the same local database and matching code as the collector.
- Unstop is no longer collected. Previously saved Unstop jobs and internships remain in local SQLite history but are hidden from API results.
- A Bank of America collector requests up to 1,000 postings each from the general and student India searches, then reads public job descriptions. It marks a truncated response as partial. The student search can legitimately return zero jobs; `stats.py --health` shows partial results if a request fails.
- Google Careers collects the combined India search for Early and Intern & Apprentice roles, follows result pages, and deduplicates job IDs. It stores the card's level and minimum qualifications as the description; incomplete searches appear as partial in `stats.py --health`.
- Mastercard now collects from its India-filtered Workday `CorporateCareers` feed as well as the existing Phenom careers feed. Shared requisition IDs avoid duplicate jobs; Workday supplies full descriptions and can refresh matching older Phenom rows. `stats.py --health` shows the Workday source separately.
- Atlassian job cards open its official details pages instead of iCIMS application dialogs. Previously saved Atlassian links are corrected in the API, and a collection run refreshes saved location and description data.

This is a prototype. Relevance scores rank jobs; they are not validated probabilities of being hired or being eligible. The last-observed date does not confirm that a listing is still open. Job sources can change or become unavailable. Application form automation is not implemented.

Barclays collects all pages of its public India search using the verified `?p=` page query and reads each official job description. It deduplicates posting IDs and reports partial results when pages, reported totals, or descriptions are incomplete.

Amazon collects the complete India search with `industry_experience=less_than_1_year` and no keyword restriction. It follows the JSON endpoint's reported total, retaining descriptions and qualifications. Failed pages, repeated pages, deadlines, or the 1,000-page safety limit produce partial source results. The app applies its existing filters after collection.

Microsoft uses India Intern and Entry searches with remote jobs included and relocation excluded. The PCSX endpoint treats a comma-separated seniority value literally, so two searches implement the selected levels and overlapping posting IDs are deduplicated. Earlier saved Microsoft rows remain in SQLite.

American Express uses the India location facet `300000000228786` from its branded careers URL through the existing Oracle endpoint. Pagination and full-description collection remain active.

Flipkart collects the public TurboHire feed linked from its official career navigation, with full descriptions, source experience, and skills. An anonymous API token is obtained in memory without an account. The static `/jobslist` page has truncated cards and nonfunctional Show More code, so its displayed count is not used. Missing records or descriptions produce partial results.

Meta Careers collects the logged-out search for Mumbai, Gurgaon, Bangalore, Hyderabad, and New Delhi offices. It discovers current public GraphQL search operations from the delivered frontend assets, requests all results, verifies the reported count, and reads descriptions, responsibilities, and qualifications from job-page structured data. Missing totals or descriptions produce partial results; unavailable search operations fail the source.

Uber collects the public `countries=India` search API, follows its page counts, deduplicates posting IDs, and stores included full descriptions. Missing pages, count mismatches, descriptions, or deadline interruptions produce partial results.

## Requirements

- Python 3.10 or newer
- Node.js and npm for the React interface
- Internet access for collecting jobs and initial dependency/model installation

No API key or `.env` file is needed for the current collectors. The database and model cache are created locally and are excluded from Git.

## Run locally

After the one-time Python setup below, double-click **`Start Job Intel.cmd`** on Windows. It installs React dependencies if needed, builds the UI if its source changed, starts FastAPI at `http://127.0.0.1:8000`, opens the browser, and runs `run.py` in another console to refresh jobs. The API and collector consoles show errors; close the API console to stop the server. Each launch starts a new collection run, so wait for an earlier run to finish before launching again. If `JOB_INTEL_OFFLINE=1`, it opens saved jobs without collection. Node.js/npm must be installed for the first build.

In PowerShell, from the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

`python run.py` fetches listings and processes new rows. The first run may take several minutes. To see source counts from the most recent run:

```powershell
python stats.py
```

For a per-platform health report based on recent collection history:

```powershell
python stats.py --health
```

It distinguishes failed or partial fetches from genuinely empty results, labels unconfigured Workable as such, and flags large drops against earlier successful runs. The baseline appears after three earlier successful nonzero runs for a platform. It does not verify whether individual saved jobs are still open.

If a source is `partial` or `failed`, its error line identifies the board or request to investigate. A 429 means that source rate limited the run; retrying immediately will not help. Postman remains disconnected after its old board returned 404. PhonePe is connected through its verified SmartRecruiters board.

## Local and offline use

All parsing, matching, storage, and UI code runs on your computer. No paid API, hosted database, account, telemetry service, or cloud inference is required. Collecting new jobs contacts public career sites. The first dependency install and model download need internet; opening employer links also needs internet.

To prepare the model explicitly while online:

```powershell
python scripts/download_model.py
```

This saves `all-MiniLM-L6-v2` under `models/`, which is excluded from Git. After dependencies and the React build are installed, you can run the API and use saved jobs without internet. In PowerShell, set strict offline mode before starting the API:

```powershell
$env:JOB_INTEL_OFFLINE = '1'
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Strict offline mode gives a clear error if the local model is missing and prevents `python run.py` from collecting jobs. `python run.py --process-only` can enrich saved rows offline. Remove the variable when you want to fetch new postings. The API should stay bound to `127.0.0.1` because it has no authentication. The React build in `ui-react/dist` is served by FastAPI, so Node is not needed to run the UI after it has been built.

Run the React interface and FastAPI in two terminals after installing the Python requirements:

```powershell
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd ui-react
npm ci
npm run dev
```

Open `http://localhost:5173`. Alternatively, run `npm run build` in `ui-react`, then serve the built interface from `http://127.0.0.1:8000` with the FastAPI command above.

## How it works

1. [`config.py`](config.py) lists companies and search filters. [`fetchers/`](fetchers/) contains separate adapters for ATS APIs and HTML career pages.
2. [`run.py`](run.py) runs the collectors, keeps India or unknown-location listings, deduplicates them, and saves them in `db/jobs.db`.
3. [`core/`](core/) classifies jobs and extracts skills and experience requirements. Resume text is extracted with PyMuPDF, `python-docx`, or UTF-8 decoding.
4. [`core/matcher.py`](core/matcher.py) embeds resume and job text, compares them with cosine similarity, then blends that score with recognized skill overlap. The React sidebar lets users correct the current resume's skills; overrides are saved by file hash in SQLite.

For the complete data flow, schema, API behavior, and code change points, see [ARCHITECTURE.md](ARCHITECTURE.md). Proposed work is tracked in [improvement.md](improvement.md).

The app is intended for local, single-user use. The FastAPI server has no authentication and should be bound to localhost. Respect each source site's access rules when running collectors.

## Repository data

`db/jobs.db` stores collected listings and local actions such as dismissals. `db/job_embeddings_cache.pt` stores generated embeddings. Both are excluded from Git, along with virtual environments, React dependencies, and build output. A fresh clone starts with an empty database until the collector runs.

Airbnb careers are included through its public Greenhouse board, with descriptions and the existing India location and app filters.

LinkedIn and Internshala collectors and sidebar links have been removed. The API hides all saved rows with their current or historical source labels; SQLite history is preserved.

Deloitte collects the official Deloitte India category `/go/Deloitte-India/718244/`, following all pages of 25 listings (up to 120 pages) and fetching descriptions with four workers. Missing pages, totals, descriptions, or deadline interruptions produce partial source health. Existing India, seniority, and resume filters apply after collection. This source does not cover the separate Deloitte USI portal.

Graviton Research Capital LLP is collected through the `gravitonresearchcapital` Greenhouse board linked by its official careers page. The live board is used instead of the site-hosted snapshot. Descriptions are included, existing India filters apply, and a valid empty jobs list is a successful fetch.

Tower Research Capital uses its official `towerresearchcapital` Greenhouse board, including descriptions. A dedicated wrapper adds country names to its known city-only location labels, preserving mixed India/overseas postings for the existing India filter. Unknown locations remain available for review. Empty boards are valid; failed requests raise source errors.

PhonePe uses SmartRecruiters tenant `PHONEPELIMITED`, verified against the 89 PUBLIC postings linked by the official careers feed. The existing adapter reads listing pages and descriptions. India ISO country code `in` is normalized to `India` to prevent confusion with the US state abbreviation.

Swiggy collects the public NextHire `reqlist/get` response used by its careers frontend, with the same careers payload. All returned postings are read in one request, deduplicated by reqId, with included descriptions and source minimum experience. Links use the frontend job-detail context. Invalid responses fail the source; malformed listings or missing descriptions produce partial results; valid empty lists succeed. The API supplies no independent total, so coverage is verified against its returned list rather than a separate vacancy count.

ZS Associates uses the public `/api/jobs` endpoint with the requested Bengaluru, Gurgaon, Noida and Pune filters. The adapter follows totalCount pagination, deduplicates IDs, includes descriptions, and uses first-party `/all/jobs/{slug}` links. Failed initial requests raise errors; interrupted pages, missing totals or descriptions produce partial results.

Rippling collects every page of its public careers search index, discovering the frontend search configuration in memory without storing keys. It deduplicates India postings by jobId, merges locations and reads public job-page descriptions. Missing pages, totals or descriptions produce partial results; configuration changes fail visibly. D. E. Shaw India reads regularJobs embedded in the official careers page, excluding exploratory applications and inactive entries; descriptions include responsibilities and qualifications. Quadeye reads the first-party Zoho-backed job-openings response used by its careers frontend, including descriptions, country fields and specific job links; no recruiter metadata is stored. The latter two feeds expose no independent total. Existing India and app filters apply. LinkedIn remains removed.

See [SOURCE_VERIFICATION.md](SOURCE_VERIFICATION.md) for the dated live checks, source counts, and current access/description limitations.

Rubrik Engineering and Information Technology & Services department pages are covered by the existing complete Greenhouse board. No extra collector is needed. Rubrik city-only locations gain the India country label when the posting's office metadata explicitly names India; the source city is preserved. Verified department India counts: Engineering 8, IT & Services 3.

### Additional company feeds (2026-10-02)

Arcesium uses its official `arcesiumllc` Greenhouse board; confirmed India city labels are normalized without changing foreign locations. Intuit uses the India country facet at `https://jobs.intuit.com/location/india-jobs/27595/1269750/2`, paginates all result pages, and fetches descriptions with four workers. Interrupted pagination or missing descriptions produces a partial result. Walmart Workday `IN ` locations and `(IND)` titles are normalized as India; `(USA)` titles identify US roles. Ambiguous multiple-location entries use public detail country metadata before filtering. Salesforce, Walmart and Palo Alto Networks now request full descriptions for India or unknown locations. Adobe remains a Phenom feed with description teasers; ServiceNow uses SmartRecruiters and Snowflake uses Ashby.

### PayPal, BlackRock and fintech source checks (2026-10-02)

PayPal has a dedicated public Workday collector (`fetchers/paypal.py`) for the `paypal/jobs` board. It discovers India location facets from the live response, paginates the scoped listings and reads full descriptions. Its requisition IDs use `R` followed by digits, without Mastercard's dash. BlackRock (`fetchers/blackrock.py`) reads all pages of its official India country facet at `https://careers.blackrock.com/location/india-jobs/45831/1269750/2` and full `.ats-description` sections; country normalization follows the country facet rather than guessing from cities. Both sources report incomplete pages or descriptions as partial.

Groww remains on Greenhouse; CRED and Meesho remain on Lever with full descriptions. Confirmed city labels on those two Lever boards are normalized to India, while foreign or unknown labels remain unchanged. Morgan Stanley remains on Eightfold with department summaries rather than full descriptions. Expedia remains on its official paginated HTML feed with team summaries; failed listing requests now raise a source failure if no jobs were collected, or return partial status if earlier pages succeeded. HTTP 403 responses were observed during verification, so Expedia is currently intermittent.

### Additional India company sources (2026-10-02)

- Greenhouse: AlphaGrep (`alphagrepsecurities`), NK Securities Research (`nksecuritiesresearch`), WorldQuant, IMC, Optiver (`optiverus`), MongoDB and Datadog. These newly added boards retain only confirmed India listings; source-specific city-only labels for AlphaGrep, WorldQuant and MongoDB are normalized before country filtering. Unresolved locations such as AlphaGrep's multiple-location submissions are omitted rather than classified as India. Existing Greenhouse board behavior is unchanged.
- Ashby: Confluent (`confluent`), scoped to India. Its branded site returned HTTP 429 during discovery; this is the current public Ashby board, not a guarantee of coverage of every hiring channel.
- `fetchers/jibe.py` supplies shared India pagination and full-description normalization for `amd.py` and `booking.py`. The public listing APIs are `careers.amd.com/api/jobs` and `jobs.booking.com/api/jobs`; country metadata takes precedence over building-specific location names. Missing pages, counts or descriptions make collection partial.
- `target.py` collects all pages of `indiajobs.target.com/search-jobs` with `?p=`, then reads full descriptions. Its India site omits card city labels, so location is India.
- `tesco.py` reads the official India search linked by Tesco Bengaluru, follows `jobOffset` pagination, checks the displayed total, and reads description fields with four workers. It includes Tesco India roles beyond technology; normal role filters still apply.
- `mediatek.py` uses the public `job.getJobs` tRPC query on `yourcareers.mediatek.com`. It checks all global result pages against the reported total, retaining Noida, Bangalore/Bengaluru and Mumbai offices. It reads the displayed city from `properties.location.code` (the API's `label` is a numeric identifier). Descriptions and model inference remain local after collection.
- `millennium.py` uses the public legacy Eightfold `/api/apply/v2/jobs` India search on `career.mlp.com`. The PCSX API is not enabled for that tenant. Listings contain department summaries, not full descriptions; count or page interruptions are partial.
- `juspay.py` monitors Juspay's official `/careers` page. Its explicit no-openings state is a successful empty collection; unavailable pages or unrecognized markup are failures. New detail markup is treated as partial pending location verification.

All source counts are live snapshots. None of these collectors applies to jobs or requires account credentials. Use `python run.py` to write new jobs to SQLite. Existing local database history is preserved.


## Requested company audit (2026-10-02)

See [COMPANY_SOURCE_AUDIT.md](COMPANY_SOURCE_AUDIT.md) for all 75 companies and live results; [COMPANY_SOURCES.json](COMPANY_SOURCES.json) defines the audit manifest. Run `python scripts/audit_company_sources.py` to refresh JSON without writing jobs to SQLite.

New India-scoped Workday collectors discover country/location facets for Broadcom, CrowdStrike, Cohesity and Postman, paginate and fetch descriptions. New Greenhouse boards cover Roku, Glean, Okta, Pure Storage, GitLab, Squarepoint and QRT. Dedicated collectors cover Netflix, Bloomberg, HRT, Automattic and Zerodha. LinkedIn employer-only guest search is explicitly partial with missing descriptions and no reliable total; the general LinkedIn job-board source remains removed. Swiggy and ZS location normalization now preserves recognized India locations.

Three companies have no verified working collector: Indeed employer, Citadel Securities and Zomato. Empty feeds, inaccessible feeds and partial results remain distinct. Automattic remote eligibility needs individual review; Zerodha nonempty schema must be verified when vacancies appear.


### Zepto Darwinbox (2026-10-02)

`fetchers/zepto.py` reads the public Darwinbox careers page with normal browser headers, then POSTs read-only listing queries to `/ms/candidateapi/job/alljobs`. It paginates against `job_counts`, normalizes source IDs and locations, decodes the full `jd`, and returns partial status for missing descriptions, malformed rows or interrupted pages. The verified live result is one Bengaluru operations job. Existing role/experience filters may exclude it. No login or application submission is used.


## UnitedHealth Group / Optum (2026-10-02)

`fetchers/unitedhealthgroup.py` collects the supplied official India keyword search through the public TalentBrew `/search-jobs/results` AJAX endpoint. Ordinary pagination links returned unrelated results, so the collector validates the requested page number and India keyword on every AJAX page, compares source totals, deduplicates IDs, and retrieves full descriptions from JobPosting structured data (longest ATS description fallback).

The live check scanned 253 search matches and returned 249 recognized India jobs, all with descriptions. Four foreign keyword matches were excluded. India location normalization requires an explicit country or a recognized Indian state; unresolved locations are excluded. This is additional to the original 75-company audit manifest. Interrupted pagination or missing descriptions returns partial status. Existing role/experience/UI filters determine which collected jobs are displayed.


## Description-based experience filtering (2026-10-04)

The default UI filter hides jobs whose description states a minimum of 2+ years. It retains 0-year, 1-year and unknown requirements. Senior/lead/manager titles no longer hide jobs or offer bulk removal. Titles are not evidence that a job accepts freshers. Experience extraction uses descriptions only, and the API re-derives the value for existing rows without rewriting SQLite. Unknown does not mean fresher eligible; preferred-only requirements remain unknown. The regex parser can miss ambiguous requirements and alternate qualification tracks, so review the original description.


## KLA India Workday (2026-10-04)

KLA is registered in `WORKDAY_INDIA` with tenant `kla`, server `wd1` and site `Search`. The shared collector discovers the board-specific India country facet, paginates and retrieves full descriptions. The supplied country value is `c4f78be1a8f14da0ab49ce1162348a5e`; hardcoding the generic `locationCountry` facet fails on this board, so facet discovery is required. Live verification returned 57 India jobs with 57 descriptions and status `ok`. Existing role and description-based experience filters apply after collection.


## Long qualification requirements (2026-10-05)

Experience extraction recognizes Basic/Required/Minimum Qualifications separately from Preferred Qualifications. Long year-to-experience clauses within required sections are supported; preferred sections cannot provide a hard minimum. The Amazon Risk Manager II example resolves to 4 years required, not its 3-year preference. Amazon truncates narrative background separately while retaining qualification sections. Existing saved descriptions are re-evaluated by the API; previously truncated descriptions require recollection to recover missing text. The parser remains heuristic for alternative qualification tracks.


### Experience section headings (2026-10-05)

The experience parser also recognizes explicit `Experience:` sections. Bosch Data Provisioning Expert (744000149775909) resolves to 5 required years; a separate preference for global-team collaboration does not override that minimum. An explicitly preferred numeric requirement remains unknown rather than a mandatory minimum.


## Windows launchers

- `Start Job Intel.cmd`: opens the site and launches `python run.py` to collect jobs (collection is skipped in offline mode).
- `Open Job Intel.cmd`: opens the site using saved jobs, without running the scraper. It calls `start.py --no-scrape`.

Both launchers build the UI if needed and start or reuse the localhost API. Double-click the desired `.cmd` file.


## Eligibility evidence and new jobs (2026-10-05)

Job details now expose an `eligibility` object from `core/eligibility.py`: description-based minimum experience, education and graduation-year evidence, explicitly mandatory skill evidence and missing recognized skills relative to the current resume. These are heuristic hints for review, not eligibility approval. Missing evidence stays unknown; preferred sections are excluded from mandatory skill extraction. No personal academic profile is inferred.

Job summaries include `first_seen_ms` (UTC milliseconds). React offers New since last visit, Refresh jobs and Mark current jobs reviewed. A localStorage checkpoint is recorded only after a successful initial load; the prior checkpoint stays fixed for that visit. First-time users see all saved jobs as new. Mark reviewed resets the boundary without dismissing jobs. State is browser-local; disabled storage loses the checkpoint between visits. Counts include all loaded jobs before other filters.

## Student opportunity discovery

The UI includes a collapsible directory of official student pages for the 30 companies and a title-based intern/apprentice/student checkbox. Amazon adds India `intern` and `apprentice` searches without the industry-experience facet; its collector deduplicates overlaps. Directory links are not vacancy records or proof of eligibility. See [STUDENT_PROGRAMS.md](STUDENT_PROGRAMS.md) for verified pages and separate-portal coverage gaps.

Morgan Stanley student programs use a separate `morgan_stanley_students` collector, reading the public `careerservice/resultset.json` endpoint with `opportunity=sg&lang=en`. The frontend paginates the complete returned array locally; the adapter verifies `totalResults`, selects explicitly India-based rows, retains descriptions and qualifications, and uses the program number as the stable ID. Missing totals, rows or descriptions mark the result partial; malformed or failed requests raise an error. The existing Eightfold India collector remains active.

### Additional student sources

The student directory contains 30 searchable company entries. `workday_students` uses `config.WORKDAY_STUDENTS` with the existing Workday India adapter. Visa's separate `Visa_Early_Careers` board collects all India roles. Walmart verifies complete India listing pagination before selecting `STUDENT_TITLE_RE` matches and fetching their descriptions; its original Global Tech search remains connected. Selection does not prove eligibility. Industrial trainee and co-op titles are included; generic graduate full-time roles are not student-title matches. IDs remain company plus requisition ID, with no new database schema. `STUDENT_PROGRAMS.md` and `STUDENT_SOURCE_AUDIT.json` record coverage and manual-only gaps. The API does not scrape program pages on UI access.

### Qualcomm India internships

`qualcomm_students` follows the supplied India `Intern` search with remote and relocation disabled and distance sorting. It verifies the count and paginates the public PCSX listing endpoint, then reads full `JobPosting` structured descriptions from first-party detail pages. Checked 2026-10-05: 2 roles, Interim Engineering Intern_2027_HW and Interim Engineering Intern_2027_SW. The earlier title count missed these underscore-separated names; the UI now normalizes underscores before student-title matching. The original general Qualcomm collector stays active. Matching saved Qualcomm IDs receive updated descriptions and reset derived enrichment fields while preserving first-seen time and dismissals. Missing descriptions or interrupted listing requests are partial; valid empty searches are successful. Program-year text is not proof of graduation eligibility.

### Netomi India searches

Netomi is registered in `config.LEVER` and collected through the existing `standard` adapter. Its public Lever board supplies both requested searches: `Remote - India` and `Gurugram`. Only those exact source locations are selected; Gurugram is normalized to `Gurugram, India`. Generic Remote and foreign locations are excluded. Descriptions combine the main text, qualification/responsibility lists and additional text, using the existing 6,000-character cap. Lever posting IDs deduplicate the board without fetching each search separately. Checked 2026-10-06: 5 Remote - India and 6 Gurugram postings. Local experience and resume filters still apply; these counts are not eligibility counts.

### Portcast India coverage

Portcast is registered in `config.LEVER`. Its Lever records can have a foreign primary `categories.location` while `categories.allLocations` lists supported Indian cities. The adapter selects explicit India locations or confirmed Delhi/Bangalore/Bengaluru/Chennai/Hyderabad/Kolkata/Mumbai labels from both fields, normalizes city-only labels to India, and excludes postings without a supported Indian location. Descriptions and qualifications use the existing Lever parser and 6,000-character cap. Checked 2026-10-06: 9 of 11 postings list Indian locations, including Data Analyst Intern whose primary location is Singapore. Normal experience and resume filters still apply; listing an Indian location does not establish applicant eligibility.

### Foreign country recognition

The shared location parser recognizes Morocco and additional explicit foreign-country labels observed in the BCG Phenom feed (including Egypt, Indonesia, Kenya, Azerbaijan, Hungary, South Africa, Colombia, Chile, Belgium, Malaysia, Czechia, Thailand, Norway, Vietnam, Peru, Greece, Türkiye and Republic of Korea). This corrects BCG requisition 56429, Delivery AI Data Engineering Intern in Casablanca, Morocco, which previously passed as Unknown. The same parser gates collection and existing API rows, so an API restart hides affected saved foreign jobs without deleting history or requiring recollection. India-containing multi-location postings and genuinely unknown locations remain visible under the existing policy. The parser remains heuristic, not an exhaustive geographic resolver.

## Resume ranking explanations

Upload a resume to rank jobs using separately embedded requirements and responsibilities, projects/work evidence, and skills weighted by required versus preferred context. Open **Why this ranking?** on a card for component scores, required skill gaps and separate eligibility checks. Education, unclear student eligibility and unclear work experience remain unknown for manual review; only explicit graduation-year statements are compared. Scores are heuristic relevance, not hiring probability. Existing location, experience and minimum-score filters still apply. Restart the backend after updating, rebuild React with `npm ci` and `npm run build`, and upload the resume again. The old embedding cache is automatically invalidated; no scraper rerun is required.

To evaluate ranking on your own labeled sample, run `python scripts/evaluate_matcher.py C:\path\to\private-labels.json`. The JSON format is documented in that script; keep personal resume text and labeled job data outside the public repository. It reports precision@10 and NDCG@10.

### Required and preferred experience visibility

The default experience filter hides postings when either the required minimum or the preferred experience lower bound is 2+ years. Preferred years are parsed separately by `extract_preferred_experience`, exposed as `preferred_experience_years` (-1 for unknown), and displayed as preferred rather than mandatory. The same rule applies to the experience bulk-removal count and action. Switching the filter off reveals these saved jobs; filtering does not delete SQLite rows. API loading recomputes both fields from saved descriptions, so restart the backend and refresh after updating; collection is unnecessary.

### Complete descriptions and experience clauses

Greenhouse and SuccessFactors preserve complete normalized descriptions. Escaped HTML is decoded before stripping tags, preventing markup from consuming the old text budget. Existing rows collected by `standard` or `successfactors` refresh changed nonempty descriptions during later runs, reset derived enrichment for reprocessing, and retain dismissal and first-seen state. Empty fetch results never replace a saved description. Existing truncated rows need a successful source refresh to recover missing text.

Experience parsing checks a year/experience clause when the legacy nearby-word scan finds no minimum, so a preceding certification preference such as “a plus” cannot erase the next bullet's numeric work requirement. Preferred sections remain excluded from mandatory minimums and are exposed separately.

## Repo review update (2026-10-07)

Experience checks now retain decimal years and the strongest independent requirement, while keeping preferred years separate. Refreshed collection results update existing descriptions and scores refresh automatically when saved content changes. Collection runs cannot overlap on the same database. For the verification scope and remaining limitations, see [REPO_REVIEW.md](REPO_REVIEW.md). The first resume upload after this update may rebuild versioned embedding cache entries.

### Runtime matcher check — 2026-10-07

The experience visibility check also considers explicit numeric experience ranges or `N+ years` in job titles, while preserving description-based required/preferred distinctions. Seniority words alone remain insufficient. This covers saved rows whose source description is empty but whose title explicitly says, for example, 8–12 years. The API exposes `description_available`; cards warn when the description is unavailable, and score explanations disclose title-only semantic comparison. Detail eligibility and ranking explanations use the same numeric experience evidence.


UBS: `fetchers/ubs.py` creates an anonymous BrassRing session, searches India,
checks the reported total and unique IDs, and retrieves each active job's full
detail sections, including skills and experience. Country and job identity are
verified; city comes from detail fields. Pagination and missing details report
partial results. Session tokens are obtained at runtime and never saved.
Existing saved descriptions refresh while retaining dismissals.

UBS also includes the supplied second board (`siteid=5131`, `LinkID=15232`).
Live verification returned four India CA Intern postings with four full descriptions.
Both boards are collected independently; shared requisition IDs are deduplicated,
and a failed board makes the combined collection partial. The original board
reported 29 jobs in the prior check; the second board adds four distinct IDs.

ION Group is configured on the shared Lever adapter (`ion`). Its public API
returned 87 global postings on October 8, 2026: 13 had explicit `country=IN`
(12 Noida and one India). Only those India records are collected. Full intro,
qualification lists and additional text are retained; usual role and experience
filters apply afterward. The supplied `lever-via` referral parameter is not
needed to read postings.

PwC India (`fetchers/pwc.py`) reads the exact experienced-jobs page's embedded
`jsondata` list, selecting explicit `iso=IND` records. Each listing links to
Workday; the collector verifies the requisition ID and India country on full
detail responses. Missing descriptions report partial collection. Existing text
refreshes without clearing dismissals. The live page exposed 635 India jobs
(636 global embedded records) on October 8, 2026, rather than the user-observed
1,660; the broader Workday board's 3,863 global total is not India coverage.

Live PwC validation completed: 635 unique India postings, 635 full descriptions,
collection status `ok`. This validation did not modify the saved job database.

LSEG Graduate Careers is configured in `WORKDAY_INDIA` (tenant `lseg`,
server `wd3`, site `Graduate_Careers`). The shared adapter discovers the
India country facet and fetches full Workday descriptions. October 8, 2026
verification returned one India posting with full description: Business Graduate
Associate (Data & Analytics), Bengaluru. Future postings remain monitored
through the same board; normal role and experience filters apply.

LSEG main Careers is also configured in `WORKDAY_INDIA` (tenant `lseg`,
server `wd3`, site `Careers`) alongside Graduate Careers. October 8, 2026
verification returned 214 India postings and 214 complete descriptions, status
`ok`. The shared adapter discovers the India facet, follows all listing pages
and retrieves full details. Shared requisition IDs use the same `lseg` company
key, avoiding duplicate saved jobs. Normal role and experience filters apply.

Electronic Arts (`fetchers/ea.py`) uses the supplied Avature India search
(`8171=[10590]`, `8171_format=5683`, `listFilterMode=1`, 20 records per page).
The collector verifies total unique role IDs, retains India scope across offsets,
and fetches complete detail fields without a character cap. Missing details or
interrupted pagination report partial results. October 10, 2026 live validation
returned 11 India roles and 11 descriptions, including six internship postings.
Saved descriptions refresh while retaining dismissals; role and numeric
experience filters apply after collection.

Swiss Re (`fetchers/swissre.py`) reads the supplied `country=IN` search with
Bangalore, Hyderabad and Mumbai city selections. All 14 cards are present in
server-rendered HTML; slider controls change visibility rather than fetch pages.
The collector checks reported total and unique IDs, requires each card's `IN`
country label, and reads full detail text from `ArticleSection .richtext`,
retaining paragraph boundaries. October 10, 2026 validation returned 14 jobs
and 14 descriptions, status `ok`. Count mismatches and missing descriptions
report partial results; saved text refreshes without clearing dismissals.

GE Appliances is configured in `WORKDAY_INDIA` (tenant `haier`, server `wd3`,
site `GE_Appliances`, company key `geappliances`). The shared adapter discovers
the India country facet, follows listing pagination and retrieves full details.
October 10, 2026 validation returned seven India jobs and seven full descriptions,
status `ok`, including Co-op/Intern and Intern - Dimensional Management. Normal
role and experience filters apply; multi-location cards retain their source label.

Bristol Myers Squibb is configured in `WORKDAY_INDIA` (tenant
`bristolmyerssquibb`, server `wd5`, site `BMS`, company key `bms`). The shared
adapter discovers exactly the supplied India facet: `locationHierarchy2` value
`7b0045a3289810548a41236822339065`. October 11, 2026 verification returned
51 unique India postings with 51 full descriptions, status `ok`. Full listing
pagination and existing role/experience filters apply; source multi-location
labels are retained under the verified India scope.

SmartRecruiters India filtering (October 11, 2026): collection now retains only
explicit `location.country=IN` records before enrichment and storage, across
Bosch, PhonePe, Freshworks and ServiceNow. The previous Bosch option only
limited description fetching, so foreign ISO-code locations entered storage as
Unknown. A source-specific location check now guards save-time and API reads
of legacy SmartRecruiters rows, including remote suffixes. Unknown country
codes are excluded for this structured source; generic-source policy is unchanged.
The local repair dismissed 26 active foreign Bosch jobs, retaining saved history
and a local dismissal-state backup. The database and backup are not published.
