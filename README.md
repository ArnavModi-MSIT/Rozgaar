# RaamBaad

A localhost workspace for collecting job listings and exporting JSON batches for manual shortlisting. Built with Python, FastAPI, React, SQLite and Playwright.

## Features

- **Career pages:** employer and ATS adapters, role/location filters, optional local resume matching, and JSON batches of 50, 100, 250 or 500 jobs.
- **URL reader:** separate browser-based readers for LinkedIn, Internshala, Naukri, Instahyre and Wellfound, with checkpoints and bounded stall recovery.
- **Review workflow:** download a batch, then optionally hide its exact members. Saved jobs, notes and application tracking stay local.
- **Description evidence:** flag missing text, department placeholders, known boilerplate and possible truncation; group repeated text without merging separate requisitions.

Collection starts only when requested in the website. The two pipelines have separate stores. Applications, sign-in and verification remain manual.

## Setup (Windows)

Requires Python **3.10**, Node.js **22** with npm, and Google Chrome. Dependencies and optional model weights require internet access during setup. Windows is the supported development environment; other platforms have not been verified.

From the repository root in PowerShell:

```powershell
py -3.10 -m venv runtime/python
& '.\runtime\python\Scripts\python.exe' -m pip install -r requirements.txt
Push-Location frontend
npm ci
npm run build
Pop-Location
```

Then double-click **Start RaamBaad.cmd**, or run:

```powershell
& '.\runtime\python\Scripts\python.exe' start.py
```

Open http://127.0.0.1:8000 and keep the launcher console open. Ctrl+C stops the platform and its owned collectors.

Resume matching uses `sentence-transformers/all-MiniLM-L6-v2` locally. To download its weights explicitly:

```powershell
& '.\runtime\python\Scripts\python.exe' -m scripts.career.download_model
```

## Usage

**Career pages:** start collection from the website, filter the list, select the JSON batch size, and download. **Remove downloaded batch** hides precisely that batch; undo restores it. Download alone does not hide jobs. Export snapshots preserve the descriptions and state at the time they were created.

**URL reader:** use **Open Reader Chrome.cmd** to open a dedicated Chrome profile. Sign in manually, then start a reader from the website. For Wellfound searches whose URL stays `/jobs`, keep exactly one filtered search open in that browser and choose filtered-tab mode. Do not change its filters during collection or resume.

Site changes, expired listings, access restrictions and incomplete source responses can cause missing data. A nonempty description, match score or successful collection does not establish source completeness, eligibility or current availability. Review official postings before applying. Use sources in accordance with their terms and your account permissions; stop collection when a site restricts access.

To attempt a repair of an older export into a **separate** reviewed JSON:

```powershell
& '.\runtime\python\Scripts\python.exe' -m scripts.career.repair_export --filename career-pages-YOUR-BATCH.json
```

Use the exact stored filename. `--latest` and `--input path/to/export.json` are also supported. Repairs leave the database and original snapshot unchanged; failed descriptions remain explicit unknowns.

## Project layout

| Directory | Purpose |
|---|---|
| `backend/api/` | Local API routes |
| `backend/core/` | Career storage, matching, exports and orchestration |
| `backend/fetchers/` | Employer and ATS adapters |
| `backend/config/` | Sources, matching rules and display names |
| `frontend/src/` | React interface |
| `url_reader/` | Browser adapters, checkpoint/history storage and watchdog |
| `raambaad/` | Shared paths and localhost launcher |
| `scripts/` | Checks, audits and maintenance tools |
| `tests/` | Synthetic unit/API tests and intercepted browser fixtures |
| `examples/` | Synthetic matcher input |
| `docs/` | Architecture, code map and reader guide |

Private state lives under ignored `runtime/`: career SQLite/resume/cache, reader JSON/history/browser profile, model weights and the Python environment. Never publish this directory or a browser profile. Local historical backups may also exist under ignored `.archive/`.

## Development checks

```powershell
& '.\runtime\python\Scripts\python.exe' -m scripts.check
& '.\runtime\python\Scripts\python.exe' -m playwright install chromium
& '.\runtime\python\Scripts\python.exe' -m scripts.check --browser
& '.\runtime\python\Scripts\python.exe' -m scripts.release_check
```

Browser fixtures intercept requests and use synthetic data; they do not prove that third-party sites currently work. Live source checks are separate, explicit actions. After UI changes, run `npm ci` and `npm run build` inside `frontend/`.

See [Architecture](docs/ARCHITECTURE.md), [Code map](docs/CODE_MAP.md), [URL reader](docs/URL_READER.md), [Contributing](CONTRIBUTING.md) and [Security](SECURITY.md).

## License

[MIT](LICENSE). Third-party dependencies retain their own licenses.
