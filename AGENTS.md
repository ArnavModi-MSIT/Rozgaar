# Guide for coding assistants

Read [ARCHITECTURE.md](ARCHITECTURE.md) before changing behavior. It describes the current collection, storage, API, matching, and React flows. Use [README.md](README.md) for setup and [improvement.md](improvement.md) for proposed work. Treat code as the source of truth if documentation has drifted; update the relevant document when you find a mismatch.

## Working model

- This is a local, single-user prototype. `python run.py` collects jobs into SQLite; FastAPI serves that database and ranks it when a resume is uploaded; React displays and filters the results.
- Collection fetchers return common job dictionaries and are registered in `core/collector.py`. Network fetching overlaps, while `run.py` writes to SQLite sequentially.
- Job categories and resume matching use `all-MiniLM-L6-v2`. Skill extraction and experience parsing are separate heuristic steps. A displayed match percentage is a ranking score, not an eligibility probability.
- The active resume and scores live in API process memory. An optional saved parsed resume and its section embeddings live in ignored `db/saved_resume.json`; the sidebar can reuse or delete that copy. Job embeddings, dismissals and resume skill overrides are also local state. Never commit saved resume files.
- The React sidebar edits the current resume's skill set through the API. Global custom-skill endpoints still have no React controls. Roadmap items are not implemented features.
- Keep inference, resume data, and storage local. `JOB_INTEL_OFFLINE=1` blocks normal collection and requires the downloaded model in `models/`; do not add a paid API or hosted runtime dependency.

## Editing this repository

- Keep source-specific HTTP and parsing logic in `fetchers/`; normalize fields before `run.py` receives them. Register new sources in `core/collector.py` and update `config.py` as needed.
- Keep schema and persistence changes in `core/storage.py`. If a stored field changes, inspect `api/data.py`, `api/main.py`, `ui-react/src/types.ts`, and consuming components together.
- Check both `core/matcher.py` and browser filters when changing ranking or visibility. Browser thresholds can hide a job even if it exists in SQLite.
- Do not delete or commit `db/jobs.db`, generated embedding caches, resumes, virtual environments, `node_modules`, or build outputs. Do not add credentials or personal resume content to examples or tests.
- Verify Python changes with focused checks and `python -m compileall -q api core fetchers run.py`; verify React changes with `npm ci` and `npm run build` in `ui-react/`. A local parser or syntax check does not prove a live career site still works.
- Run `python -m unittest discover -s tests -v` for offline collector and source-health regressions. When adding a fetcher, distinguish a complete empty result from an interrupted fetch; the `fetchers.result.CollectionResult` status is available for partial results.
- Update [ARCHITECTURE.md](ARCHITECTURE.md) and [README.md](README.md) when data flow, commands, API contracts, or user-visible behavior changes.

## Local workspace layout

The outer folder now contains only the two CMD launchers, `.venv/`, and `app/`. This file and application source live in `app/`; run manual commands from here. Use `..\.venv\Scripts\python.exe` locally. The source-only GitHub checkout is `public-release/` inside this directory; preserve the original repository history and mirror authorized source changes to that checkout. Do not move the existing virtual environment or publish the database. The CMD launchers work with both organized and flat layouts.
