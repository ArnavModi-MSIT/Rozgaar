# Job Intel Platform

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

If a source is `partial` or `failed`, its error line identifies the board or request to investigate. A 429 means that source rate limited the run; retrying immediately will not help. The Postman and PhonePe Greenhouse board slugs were removed after both returned 404 on 1 October 2026; their official career pages need separately verified adapters before they can be collected again.

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
