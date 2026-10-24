# RaamBaad editing guide

Read `README.md`, `docs/CODE_MAP.md` and `docs/ARCHITECTURE.md` before changing behavior.

- `backend/api/` exposes FastAPI routes; `backend/core/` owns career storage, matching and orchestration; `backend/fetchers/` contains career-source adapters.
- `frontend/src/` is the React UI. Keep collection, export and reader views in their own components.
- `url_reader/sources/` contains browser-site adapters; `url_reader/browser/` owns pagination and parallel workers; `url_reader/storage/` owns checkpoints and duplicate history. `engine.py` coordinates collection; `supervisor.py` bounds stalled runs.
- Import explicit packages (`backend.core`, `url_reader.sources`), never extend `sys.path` to import sibling code. Shared filesystem locations live in `raambaad/paths.py`.
- Career data and reader data remain separate. Never import reader output into the career database. Startup must not start collection.
- Preserve saved jobs, export snapshots, tracking/removal state, resumes, browser profile and Git history. `runtime/` and `.archive/` are private and excluded from Git. Never add their contents to source control.
- This is a local single-user app. Keep matching and storage local; no paid API/hosting dependency. Account verification and application submission remain manual.
- Use `runtime/python/Scripts/python.exe`. Run `python -m unittest discover -s tests -t . -p "test_*.py" -q` and `python -m compileall -q backend url_reader raambaad scripts` from the repository root after Python changes.
- After React changes run `npm ci` and `npm run build` from `frontend/`. Browser fixtures are under `tests/reader/` and intercept all requests; they must not collect real LinkedIn data.
- One canonical checkout now replaces the former nested repositories and mirrored release checkout. Prior source snapshots, repository metadata and local artifacts are retained under ignored `.archive/reorganization-20261023/`; do not create duplicate active source trees.
- Update the code map and relevant guide when module locations, commands or behavior change. Do not push or rewrite history without explicit authorization.
