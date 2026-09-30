# Job Intel Platform

A local job discovery prototype for students and early career applicants in India. It collects public job listings from supported career sites, stores them in SQLite, and ranks them against an uploaded resume.

## What works

- Platform-specific collectors for career sites and job boards, with a shared job format.
- Location filtering, duplicate detection, last-observed dates, job classification, skill extraction, and experience extraction.
- PDF, DOCX, and TXT resume upload (5 MB limit). Matching combines `all-MiniLM-L6-v2` semantic similarity with explicit skill overlap. Resume skills can be corrected in the React sidebar.
- React interface backed by FastAPI, using the same local database and matching code as the collector.

This is a prototype. Relevance scores rank jobs; they are not validated probabilities of being hired or being eligible. The last-observed date does not confirm that a listing is still open. Job sources can change or become unavailable. Application form automation is not implemented.

## Requirements

- Python 3.10 or newer
- Node.js and npm for the React interface
- Internet access for collecting jobs and initial dependency/model installation

No API key or `.env` file is needed for the current collectors. The database and model cache are created locally and are excluded from Git.

## Run locally

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

It distinguishes failed or partial fetches from genuinely empty results and flags large drops against earlier successful runs. It does not verify whether individual saved jobs are still open.

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
