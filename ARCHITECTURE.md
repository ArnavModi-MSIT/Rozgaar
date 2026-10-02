# Architecture and code guide

This document describes the code in this repository as it currently works. Read it with [README.md](README.md) for setup and [improvement.md](improvement.md) for proposed work. Planned items in the improvement roadmap are not part of the current system.

## System boundary

Job Intel is a **local, single-user** application. It has two separate execution paths:

1. `python run.py` collects and processes postings, then writes `db/jobs.db`.
2. FastAPI reads that database and serves a React UI. The user may upload a resume to rank the saved postings.

There is no background scheduler, hosted service, login system, application submission bot, or cloud database. Run commands from the repository root because the Python code uses relative `db/` paths. Collection is the network step; parsing, matching, and the UI run locally. To enforce offline mode, download the model with `python scripts/download_model.py` once, then set `JOB_INTEL_OFFLINE=1`. Normal collection refuses to run in that mode; `--process-only` remains available.

On Windows, `Start Job Intel.cmd` invokes `start.py` from the repository root. After the one-time Python setup, the launcher builds the React bundle if missing or stale, starts the localhost FastAPI server if it is not already responding, opens the browser, and starts one collection process. It skips collection when `JOB_INTEL_OFFLINE=1`. Each double-click launches another collection, so it is not a scheduler or process supervisor.

```mermaid
flowchart LR
    S[Career sites and job boards] --> F[fetchers/]
    C[config.py] --> F
    F --> R[run.py]
    R --> P[core/ storage, dedup, location, skills, experience, classification]
    P --> D[(db/jobs.db)]
    D --> A[api/data.py and api/main.py]
    M[all-MiniLM-L6-v2] --> P
    M --> A
    A --> U[React UI in ui-react/]
    U -->|resume upload, filters, dismissals| A
    A --> E[(db/job_embeddings_cache.pt)]
```

The embedding cache is generated locally. The React client does not fetch career sites itself.


Unstop is not registered as a collector. The API excludes all previously saved Unstop rows from results without deleting local SQLite history.


The Atlassian adapter reads its first-party listings endpoint and builds first-party `/company/careers/details/{id}` links. The endpoint's `applyUrl` points to an iCIMS application dialog and is unsuitable for the job card. Existing saved Atlassian URLs are normalized when the API loads them; a later collector run also refreshes saved locations and descriptions while keeping job IDs and dismissals. A failed listings request now raises a source error instead of appearing as an empty successful fetch.

The Bank of America adapter reads the public JSON requests behind the general and student India search pages. The site's offset query currently returns no rows after the first page, so the adapter requests up to 1,000 results from offset zero and checks the count against the reported total. It deduplicates requisition IDs and reads each public detail page for the description. A valid zero-result student search is successful; a truncated response, failed request, or missing description makes the source partial when other jobs were fetched.

The Google Careers adapter collects one India search with repeated `target_level=EARLY` and `target_level=INTERN_AND_APPRENTICE` parameters. It parses server-rendered cards, follows the displayed total through pages of 20 with a 50-page safety limit, and deduplicates job IDs. Its description contains the card's level and minimum qualifications rather than full detail-page text. Missing pages or result counts mark the source partial. Previously collected rows remain in local SQLite history.

Mastercard is collected from both its Phenom careers site and the `CorporateCareers` Workday page. The dedicated `mastercard_workday` source discovers India location IDs from Workday's current facet response, fetches all India listing pages, and reads full job descriptions. It runs before Phenom; both feeds use `mastercard:R-...` as the stable ID, so overlapping postings are saved once and Phenom can still supply postings absent from Workday. When an existing Phenom row receives a full Workday description, its source, URL, and content are refreshed while its ID and dismissal stay intact. A failed page or description produces a partial Mastercard Workday run.

Barclays collects every page of its public India search using `?p=` and reads official job descriptions. Posting IDs are deduplicated; incomplete pages, totals, or descriptions produce a partial source result.

Amazon collects the complete India search with `industry_experience=less_than_1_year` and no keyword restriction. It follows the JSON endpoint's reported total, retaining descriptions and qualifications. Failed pages, repeated pages, deadlines, or the 1,000-page safety limit produce partial source results. The app applies its existing filters after collection.

Microsoft uses India Intern and Entry searches with remote jobs included and relocation excluded. The PCSX endpoint treats a comma-separated seniority value literally, so two searches implement the selected levels and overlapping posting IDs are deduplicated. Earlier saved Microsoft rows remain in SQLite.

American Express uses the India location facet `300000000228786` from its branded careers URL through the existing Oracle endpoint. Pagination and full-description collection remain active.

Flipkart collects the public TurboHire feed linked from its official career navigation, with full descriptions, source experience, and skills. An anonymous API token is obtained in memory without an account. The static `/jobslist` page has truncated cards and nonfunctional Show More code, so its displayed count is not used. Missing records or descriptions produce partial results.

Meta Careers collects the logged-out search for Mumbai, Gurgaon, Bangalore, Hyderabad, and New Delhi offices. It discovers current public GraphQL search operations from the delivered frontend assets, requests all results, verifies the reported count, and reads descriptions, responsibilities, and qualifications from job-page structured data. Missing totals or descriptions produce partial results; unavailable search operations fail the source.

Uber collects the public `countries=India` search API, follows its page counts, deduplicates posting IDs, and stores included full descriptions. Missing pages, count mismatches, descriptions, or deadline interruptions produce partial results.

## Repository map

| Path | Responsibility |
| --- | --- |
| `config.py` | Configured companies, ATS tenants, display names, location and title patterns. |
| `fetchers/` | One adapter per ATS or site; handles HTTP, pagination, parsing, and source-specific fields. |
| `fetchers/http_client.py` | Shared JSON/text request helpers with retries for rate limits, server errors, and timeouts. Some older fetchers still have their own request code. |
| `core/collector.py` | `PLATFORMS` registry mapping source names to collector calls. `collect_all()` is a diagnostic helper; normal runs use `run.py`. |
| `run.py` | Main collection and processing entry point. Fetches platforms concurrently, writes sequentially, then enriches unprocessed rows. |
| `core/storage.py` | SQLite schema, migrations, job IDs, inserts, dismissal, skill overrides, run stats, and cleanup. |
| `core/dedup.py`, `core/location.py` | Repost key and location parsing. |
| `core/classify.py`, `core/skills.py`, `core/experience.py` | Job category, recognized skills, and minimum experience extraction. |
| `core/embeddings.py`, `core/matcher.py`, `core/resume_text.py` | Shared model loader, resume-to-job ranking and embedding cache, resume text extraction. |
| `api/main.py`, `api/data.py` | HTTP endpoints and SQLite/DataFrame-to-JSON adapter; currently loaded resume and scores live in process memory. |
| `ui-react/src/` | React components, browser-side filtering and display, API wrapper, and explicit TypeScript response types. |
| `stats.py`, `debug/` | Local diagnostics. |

`core/filters.py` contains an older `matches()` hard filter but **normal collection does not call it**. The older `config.INCLUDE` and `config.EXCLUDE` patterns are not save-time gates. Do not describe them as active collection filters.

## Collection path

### Fetcher contract

Each collector returns job dictionaries with the common fields below. The collector passes the source name separately to `save_job()`.

```python
{
    "company": "example",
    "source_id": "source posting ID",  # may be absent for some sources
    "title": "Data Analyst",
    "location": "Delhi, India",
    "url": "https://...",
    "description": "Source description text or HTML",
}
```

The `standard` adapter handles Greenhouse, Lever, and Ashby. Its HTTP connection pool matches its 16 board-fetch workers. Postman was removed from Greenhouse after a 404. PhonePe is now collected through SmartRecruiters. Other adapters cover Oracle, Workday, SmartRecruiters, SuccessFactors, Phenom, iCIMS, Eightfold, Workable, Bank of America, Google Careers, Amazon, and several company-specific sites. Most use public JSON endpoints; some parse HTML. An adapter must normalize the same fields even if its source uses different names. `config.WORKABLE` is currently empty, so the registered Workable collector is reported as skipped rather than as a successful zero-job fetch.

### What `python run.py` does

1. `init_db()` creates or migrates SQLite tables. The database directory is created at `run.py` import time.
2. `run.py` preloads existing IDs and repost keys from **all** saved jobs, including dismissed ones.
3. It submits every entry in `core.collector.PLATFORMS` to a thread pool with one shared deadline (`RUN_DEADLINE_SECONDS`, default 600 seconds). Network fetching overlaps; SQLite writes happen in the main thread.
4. For each returned posting, it drops locations confidently outside India. The parser recognizes country names, US state names and abbreviations, and several unambiguous US city-only locations. Unknown locations are kept. It updates `last_seen` for an existing `job_id`, then checks the repost key for new IDs, then inserts new jobs. Matching existing Atlassian rows refresh their URLs, locations, and descriptions. Missing postings are never automatically marked closed.
5. It writes one `run_stats` row per platform. A raised platform error receives `status='failed'`; the standard ATS and Mastercard Workday collectors can also return `status='partial'` when some boards, pages, or descriptions fail. Their reasons are saved in `run_stats.error`. Some other platforms still return plain job lists and cannot yet signal internal partial failure. The legacy `jobs_matched` statistic currently equals `jobs_fetched` and is **not** a count of resume matches.
6. `process_backlog()` fills missing category, skills, and experience fields. The three processors have separate error handling, so a classification failure does not prevent skill or experience extraction.
7. It removes rows whose `first_seen` is older than 365 days. This is age-based cleanup, not verification that a posting is still open.

The stable ID is `company:source_id` when the source provides an ID; otherwise it is a hash of company, title, and URL. The repost key is `(company, normalized title, parsed city, normalized description fingerprint)`. It can catch a repost with a new source ID, but it is not a perfect cross-site identity system. Dismissed jobs remain in dedup sets so they do not reappear simply because an employer reposted them.

The API applies the same India-or-unknown country rule when loading previously saved jobs. This hides older foreign rows after a parser correction without deleting them from SQLite. The React location checkboxes are additional user filters, not the country gate.

### Enrichment

- **Category:** `core/classify.py` embeds each job's title and description and compares it with short category descriptions. It uses the shared `all-MiniLM-L6-v2` model. A low best similarity falls back to `Other`.
- **Skills:** `core/skills.py` uses case-insensitive regular expressions over a curated skill list plus any custom keywords stored in SQLite. This is keyword extraction, not an ML skill parser. Jobs store comma-separated recognized skills.
- **Experience:** `core/experience.py` looks near mentions of “experience” for year requirements and distinguishes required from preferred wording. `NULL` means not processed; `-1` means processed but unknown; `0` is an explicit fresher signal; positive values are extracted minimum years. Mixed-track postings can still be misread.

`process_backlog()` only handles rows with a `NULL` value in one of those fields. Updating an extraction rule does not automatically rewrite already processed jobs; use the relevant reprocess command.

## SQLite and local state

`core/storage.py:init_db()` owns the schema and simple additive migrations:

| Table | Important fields | Purpose |
| --- | --- | --- |
| `jobs` | `id`, `company`, `title`, `location`, `url`, `description`, `source`, `first_seen`, `last_seen`, `dismissed`, `category`, `skills`, `experience_years` | Saved postings and derived fields. `last_seen` is the latest observation of an exact source ID, not confirmed open status. The `score` column is legacy and not the current resume match. |
| `run_stats` | `run_id`, `timestamp`, `platform`, fetched/saved counts, runtime, `status`, `error` | Per-platform collection history. |
| `custom_skills` | `skill` | User-added terms used by the regex skill extractor. |
| `resume_skill_overrides` | `resume_key`, `skills` | Corrected skill set keyed by SHA-256 of the uploaded file bytes. |

`db/jobs.db` and `db/job_embeddings_cache.pt` are ignored by Git. The full resume text is **not stored in SQLite**: `api/data.py` keeps the current resume text, key, skill set, and per-job scores in a module-level `_resume` dictionary. Restarting the API clears that live state; saved skill overrides remain in SQLite. This design is only suitable for one local user and one API process.

## Resume upload and ranking

1. React sends a PDF, DOCX, or TXT file to `POST /api/resume` as multipart form data. The API rejects unsupported extensions and files larger than 5 MB.
2. `api/main.py` hashes the file bytes and adapts FastAPI's `UploadFile` to the file-like interface of `core/resume_text.py`.
3. The parser uses PyMuPDF for PDF text, `python-docx` for paragraphs and table cells, and UTF-8 decoding for TXT. Empty extracted text is rejected. There is no OCR for scanned PDFs.
4. The API extracts recognized resume skills. If `resume_skill_overrides` has a saved set for the file hash, that corrected set takes precedence.
5. `api/data.py:set_resume()` calls `rescore()`. It loads or incrementally computes job embeddings and calls `rank_by_resume()`.
6. Scores are held in memory as `{job_id: match_pct}` and included in later `/api/jobs` responses.

`core/embeddings.py` lazily loads one `all-MiniLM-L6-v2` model for classification and matching within each Python process. It prefers the project-local `models/all-MiniLM-L6-v2`; outside strict offline mode it can still download the model on first use if that directory is absent. Job embeddings represent title plus description (capped at 2,500 characters). The resume input is capped at 5,000 characters, and the model sequence limit is set to 512 tokens. Later text can still be truncated by the tokenizer. Each cached job embedding is keyed by job ID plus a content hash, so unchanged jobs do not need to be re-embedded; the cache is saved with PyTorch under `db/`.

The current match formula is:

```text
semantic = cosine(job_embedding, resume_embedding)
semantic_pct = 100 * (clip(semantic, 0.15, 0.65) - 0.15) / 0.50
skill_pct = 100 * (recognized job skills also in resume) / (recognized job skills)
skill_weight = 0.40 * min(1, number_of_recognized_job_skills / 3)
score = (1 - skill_weight) * semantic_pct + skill_weight * skill_pct
```

If a job has no recognized skills, it uses semantic score alone. If neither its title matches `config.TARGET_ROLE_RE` nor its skill overlap reaches 40%, the score is capped at 10. The values are configured in `core/matcher.py`; they are heuristics, not calibrated probabilities of eligibility or hiring. The job category classifier uses embeddings too, but it is a separate step and its category label is not the match percentage.

The React sidebar calls `PUT /api/resume/skills` to save corrections to the current resume and rescore. The API also exposes custom-skill endpoints, but the React UI does not yet manage the global custom-skill vocabulary. Existing job skill lists require `--reprocess-skills` after that vocabulary changes.

## HTTP and browser behavior

`api/main.py` defines the endpoints; `api/data.py` creates list and detail payloads. Main routes:

| Route | Behavior |
| --- | --- |
| `GET /api/jobs`, `GET /api/jobs/{id}` | Lists all non-dismissed jobs, then fetches description and experience lines for one job on demand. The list omits descriptions to reduce payload size. |
| `GET /api/stats` | Count of visible jobs, distinct companies, and whether a resume is loaded. |
| `POST /api/resume`, `GET /api/resume`, `DELETE /api/resume` | Upload and score a resume; inspect or clear process-memory resume state. |
| `PUT /api/resume/skills` | Save a corrected skill set for the current resume and rescore. |
| `GET/POST /api/custom-skills`, `DELETE /api/custom-skills/{skill}` | Read, add, or remove custom skill terms. Existing job rows need `--reprocess-skills` after taxonomy changes. |
| `POST /api/jobs/{id}/dismiss`, `POST /api/jobs/dismiss-bulk` | Persist `dismissed=1` and invalidate the 30-second job DataFrame cache. |

The API reads non-dismissed jobs from SQLite into a Pandas DataFrame, computes derived location flags and the `is_senior` flag, then serializes list rows. `ui-react/src/types.ts` manually mirrors those JSON fields. Update both sides when the API contract changes.

The React app fetches the full list once per refresh and filters in browser memory. Its default filter hides jobs with a known requirement of **1 or more years**; unknown experience (`-1`) stays visible. Location text is a substring search; Remote/NCR/India checkboxes combine with OR. With a resume loaded it hides scores below 20 and sorts by score; otherwise it sorts by `first_seen`. It displays 40 rows at first and reveals more in batches. Opening a job link dismisses it only when the optional auto-remove toggle is enabled; the toggle defaults to off. Dismissal is stored in SQLite. The React UI does not currently distinguish “applied” from “not interested.”

In development, Vite on port 5173 proxies `/api` to FastAPI on `127.0.0.1:8000`. After `npm run build`, `api/main.py` serves the `ui-react/dist` index and assets from the API origin. The built directory is generated and ignored by Git.

## Commands and change points

| Task | Command or file |
| --- | --- |
| Fetch and process postings | `python run.py` |
| Process only rows with missing derived fields | `python run.py --process-only` |
| Recalculate every job's skill list | `python run.py --reprocess-skills` |
| Recalculate every job's experience requirement | `python run.py --reprocess-experience` |
| Remove jobs older than 365 days | `python run.py --cleanup` (also runs after a normal collection) |
| Inspect collection history | `python stats.py`, `python stats.py --summary`, `python stats.py --all`, or `python stats.py --health` |
| Add or change a company | Edit `config.py` and the relevant `fetchers/` adapter. |
| Add a platform | Write an adapter returning the common job dictionary, then register it in `core/collector.py`. |
| Change score behavior | Inspect `core/matcher.py`, `core/skills.py`, `config.TARGET_ROLE_RE`, and the browser's fixed 20-point display threshold together. |
| Change UI fields | Update `api/data.py`, `api/main.py`, `ui-react/src/types.ts`, and consuming components together. |

The offline fixture tests in `tests/` cover Greenhouse, source-health classification, and the `run_stats` migration. Run `python -m unittest discover -s tests -v`. `python -m compileall -q api core fetchers run.py stats.py` checks syntax; `npm ci && npm run build` checks the React build. Live source behavior requires separate network checks because source sites can change. There is no CI yet.

## Important limits

- A stored posting is not guaranteed to be open today; `last_seen` records an observation, but there is no confirmed-closed workflow. Old rows migrated from earlier versions start with `last_seen = first_seen`.
- Save-time filtering only rejects confidently non-India locations. Unknown locations are kept and treated as potentially India-relevant in the UI.
- Resume scoring and category assignment have no labeled evaluation in this repo. Match percentages are ranking heuristics.
- The API has no authentication, per-user state, upload-size limit, or multi-user isolation. Bind it to localhost.
- Browser application automation and automatic submission are not implemented.

Use [improvement.md](improvement.md) for proposed changes, not as evidence that those features already work.

### Airbnb collection

Airbnb uses the existing standard Greenhouse collector (`airbnb` board). The board returns all postings in one request with descriptions; `run.py` applies the shared India-or-unknown location filter before saving. The five India posting IDs on the official filtered careers page matched the feed during verification. App filters can hide saved roles based on experience or resume matching.

LinkedIn and Internshala collectors and sidebar links have been removed. The API hides all saved rows with their current or historical source labels; SQLite history is preserved.

Deloitte collects the official Deloitte India category `/go/Deloitte-India/718244/`, following all pages of 25 listings (up to 120 pages) and fetching descriptions with four workers. Missing pages, totals, descriptions, or deadline interruptions produce partial source health. Existing India, seniority, and resume filters apply after collection. This source does not cover the separate Deloitte USI portal.

Graviton Research Capital LLP is collected through the `gravitonresearchcapital` Greenhouse board linked by its official careers page. The live board is used instead of the site-hosted snapshot. Descriptions are included, existing India filters apply, and a valid empty jobs list is a successful fetch.

Tower Research Capital uses its official `towerresearchcapital` Greenhouse board, including descriptions. A dedicated wrapper adds country names to its known city-only location labels, preserving mixed India/overseas postings for the existing India filter. Unknown locations remain available for review. Empty boards are valid; failed requests raise source errors.

PhonePe uses SmartRecruiters tenant `PHONEPELIMITED`, verified against the 89 PUBLIC postings linked by the official careers feed. The existing adapter reads listing pages and descriptions. India ISO country code `in` is normalized to `India` to prevent confusion with the US state abbreviation.

Swiggy collects the public NextHire `reqlist/get` response used by its careers frontend, with the same careers payload. All returned postings are read in one request, deduplicated by reqId, with included descriptions and source minimum experience. Links use the frontend job-detail context. Invalid responses fail the source; malformed listings or missing descriptions produce partial results; valid empty lists succeed. The API supplies no independent total, so coverage is verified against its returned list rather than a separate vacancy count.
