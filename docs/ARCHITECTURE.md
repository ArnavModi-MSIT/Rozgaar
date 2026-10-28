# Architecture

Rozgaar is a local, single-user application. The launcher serves the React build and FastAPI on `127.0.0.1:8000`. Startup does not collect jobs. Shared filesystem locations are defined in `rozgaar/paths.py`.

## Career pipeline

`backend/core/collector.py` registers source adapters from `backend/fetchers/`. `backend/collector.py` coordinates bounded collection and SQLite persistence. Adapters return normalized postings; some also return explicit partial-source results. Coverage varies by adapter and employer. Missing data must not be interpreted as a successful empty source.

HRT and Expedia are disabled due to access restrictions and are absent from the registered collectors. `DISABLED_CAREER_SOURCES` in `backend/config/sources.py` records their URLs and reasons; the generated inventory lists them separately. Saved data and historical source health remain intact. Retained adapter modules do not run automatically.

The 26 October employer batch lives in `backend/config/career_expansion.py` and is registered into existing inventories by `sources.py`. New standard boards require positive India evidence; generic remote/unknown locations are excluded. `python -m scripts.career.company_inventory` regenerates the complete Markdown inventory offline. Live listing/sample-description checks and salary limitations are recorded separately in `docs/catalog/CAREER_EXPANSION_20261026.md`.

Info Edge's Zwayam adapter uses a single short-lived PowerShell 7 helper for public search/detail HTTP/2 calls. Python owns pagination, company/job identity checks, India filtering, full-text assembly and partial-result status. The helper accepts only fixed search/detail operations for company 15578; it never accepts arbitrary URLs or executes supplied code. It has no browser/account dependency and exits when collection completes. No job or applicant state is written by the helper.

Career SQLite lives in `runtime/career/`. Collection uses a process lock. Matching combines local skill/experience heuristics with optional sentence-transformer embeddings. Relevance scores are separate from eligibility decisions.

`backend/core/career_exports.py` saves durable JSON snapshots with exact batch membership. Downloading and removing are separate operations. Removing a batch hides its exact jobs and preserves the snapshot. `description_quality.py` adds conservative text-quality labels and exact normalized-text groups; it does not deduplicate requisitions or guarantee completeness. `scripts/career/repair_export.py` creates a separate reviewed file without changing the original snapshot or database.

Career JSON sizes are 50, 100, 250, 500 or 1,000 jobs. The API and snapshot validator enforce the selected limit; fewer matching jobs are allowed. Download, removal and undo preserve exact snapshot membership at every supported size.

## URL-reader pipeline

`url_reader/engine.py` coordinates site adapters in `url_reader/sources/`. Browser navigation, parallel detail workers and pagination live in `url_reader/browser/`. Checkpoints, duplicate history and locking live in `url_reader/storage/`.

The reader connects through Playwright/CDP to a dedicated debug-enabled Chrome profile. Sign-in and verification are manual. Captured Wellfound searches use the existing filtered tab and validate its visible filter scope. The supervisor bounds stalls and preserves checkpoint progress; cleanup targets reader-owned tabs.

Reader JSON/history/profile files live under `runtime/reader/`. They are not imported into the career database. Legacy import compatibility routes do not enable synchronization.

## API and frontend

`backend/api/main.py` exposes job, resume and tracker routes. `backend/api/platform.py` controls the two pipelines and career exports. React components keep career collection, JSON export and URL-reader controls separate. The service is intended for loopback use, not shared hosting.

Runtime source fingerprints let the launcher detect stale local servers. The launcher builds changed frontend source when needed. A running process must be restarted to load Python changes.

## Validation and boundaries

Unit/API tests use synthetic data and temporary stores. Browser fixtures intercept network requests and do not collect real account data. Live collection and model download are explicit actions outside offline checks.

Do not commit SQLite stores, exports, resumes, browser profiles, model weights, logs or local backups. Source inventories in `docs/catalog/COMPANY_SOURCES.json` describe configuration, not verified live coverage. Audit output belongs under `runtime/artifacts/`.

HTTP connection reuse is bounded at 16 connections per host for standard boards and 40 for SmartRecruiters (eight boards with five detail workers each). Info Edge can discover a full portable PowerShell distribution in ignored `runtime/tools/powershell/` when the launcher PATH lacks `pwsh`.

HTTP connection reuse is bounded at 16 connections per host for standard boards and 40 for SmartRecruiters (eight boards with five detail workers each). Info Edge can discover a full portable PowerShell distribution in ignored `runtime/tools/powershell/` when the launcher PATH lacks `pwsh`.
