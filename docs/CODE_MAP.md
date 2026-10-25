# Code map

## Edit locations

| Task | Files |
|---|---|
| Start localhost / check build freshness | `start.py`, `rozgaar/launcher.py` |
| Change data, model or browser paths | `rozgaar/paths.py` |
| Add or edit employer inventories | `backend/config/sources.py` |
| Change role/location matching rules | `backend/config/matching.py` |
| Change company display names | `backend/config/display.py` |
| Add a career-site adapter | `backend/fetchers/`, register in `backend/core/collector.py` |
| Change career collection persistence | `backend/collector.py`, `backend/core/storage.py` |
| Change JSON limits, snapshots or removal | `backend/core/career_exports.py`, `backend/api/platform.py` |
| Label insufficient, possibly truncated or repeated descriptions | `backend/core/description_quality.py` |
| Repair a snapshot into a separate reviewed JSON | `scripts/career/repair_export.py` |
| Change resume ranking or eligibility | `backend/core/matcher.py`, `match_sections.py`, `eligibility.py`, `experience.py` |
| Change the career JSON controls | `frontend/src/components/CareerExportPanel.tsx` |
| Change experience limits and bulk removal | `frontend/src/experience.ts`, `frontend/src/components/Sidebar.tsx`, `frontend/src/App.tsx` |
| Change the URL-reader controls | `frontend/src/components/UrlReaderPanel.tsx` |
| Change browser-site extraction | `url_reader/sources/` |
| Change pagination or concurrent readers | `url_reader/browser/` |
| Change resume/checkpoint validation | `url_reader/storage/checkpoints.py`, `url_reader/engine.py` |
| Change seen-posting history | `url_reader/storage/history.py` |
| Reset only Wellfound checkpoints and seen history | `scripts/reset_wellfound.py` |
| Change stall recovery | `url_reader/supervisor.py` |
| Change dedicated Chrome startup | `scripts/open_reader_browser.ps1` |
| Run all checks | `runtime/python/Scripts/python.exe -m scripts.check --browser` |

## Data and process boundaries

Career SQLite and reader JSON/history stay separate. FastAPI mounts the React build and controls both collectors. Career collection runs as `python -m backend.collector`; the reader watchdog runs `python -m url_reader.supervisor`. Both use the repository root as their working directory. The Wellfound inspector runs its own bounded module subprocess. Startup never launches either collector.

`runtime/` contains private state and dependencies; `.archive/` contains old checkouts and migration evidence. They are not editable source or publication inputs. There is no active duplicate release checkout.


## Publication checks

Dated source endpoint changes and verification limits are recorded in [Source maintenance](SOURCE_STATUS.md).

`scripts/release_check.py` scans candidate files and all locally reachable Git blobs for private artifacts and selected credential patterns. It reports locations without printing matched values. The scan is heuristic; it does not certify the absence of secrets.
