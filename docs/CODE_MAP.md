# Code map

## Edit locations

| Task | Files |
|---|---|
| Start localhost / check build freshness | `start.py`, `rozgaar/launcher.py` |
| Change data, model or browser paths | `rozgaar/paths.py` |
| Add or edit employer inventories | `backend/config/sources.py`, `backend/config/career_expansion.py` (26 October batch) |
| View disabled career sources and reasons | `backend/config/sources.py` (`DISABLED_CAREER_SOURCES`), disabled section of `docs/catalog/CAREER_COMPANIES.md` |
| View/regenerate configured career-page companies | `docs/catalog/CAREER_COMPANIES.md`, `python -m scripts.career.company_inventory` |
| View added-source checks and unresolved companies | `docs/catalog/CAREER_EXPANSION_20261026.md`, `docs/catalog/CAREER_SOURCES_TO_FIND.md` |
| Reject malformed Workday cards / hide legacy blank titles | `backend/fetchers/workday.py`, `backend/api/data.py` |
| Change role/location matching rules | `backend/config/matching.py` |
| Change company display names | `backend/config/display.py` |
| Add a career-site adapter | `backend/fetchers/`, register in `backend/core/collector.py` |
| Change HRT Mumbai search | `backend/fetchers/hrt.py` (filtered source URL and Mumbai-only result guard) |
| Change Expedia India search | `backend/fetchers/expedia.py` (country filter in pagination and India-only result guard) |
| Change public listing retries/errors | `backend/fetchers/http_client.py`, `eightfold.py`, `qualcomm_students.py`, `expedia.py` (bounded rate-limit waits; preserve partial pages) |
| Change IBM India pagination/full descriptions | `backend/fetchers/ibm.py` (public search API, stable document ordering) |
| Change Info Edge/Zwayam collection | `backend/fetchers/infoedge.py`, `scripts/career/zwayam_http.ps1` (public HTTP/2 transport; PowerShell 7) |
| Change Siemens Software India collection | `backend/fetchers/siemenssoftware.py` (employer-scoped DE Jobs search and full detail JSON) |
| Change Barracuda Bangalore collection | `backend/fetchers/barracuda.py` (public careers-room JSON, exact Bangalore scope) |
| Change Axtria India/FDE India collection | `backend/fetchers/axtria.py` (official cards and identity-checked public SuccessFactors descriptions) |
| Change BMC Software India collection | `backend/fetchers/bmcsoftware.py` (scoped Avature pagination and validated detail sections) |
| Change NCR Voyix APAC India board | `backend/config/sources.py` (`ncrvoyix`, `ext_apac`, India applied facet), `backend/fetchers/workday.py` |
| Change Teradata India collection | `backend/fetchers/teradata.py` (GR8 People public search and full descriptions) |
| Change Rocketlane Kula board | `backend/config/sources.py` (`rocketlane` employer portal), `backend/fetchers/employer_portals.py` (`fetch_kula`) |
| Change Sprinto Lever India scope | `backend/config/sources.py` (case-sensitive `Sprinto` account), `backend/fetchers/standard.py` |
| Change HSBC India collection | `backend/fetchers/hsbc.py` (Eightfold apply-v2 search and full job descriptions) |
| Change Publicis Sapient India collection | `backend/fetchers/publicissapient.py` (public pagination and full embedded detail sections) |
| Change Josh Technology Group HTML collection | `backend/fetchers/joshtechnologygroup.py` (scoped list and full detail pages) |
| Change career collection persistence | `backend/collector.py`, `backend/core/storage.py` |
| Change JSON limits, snapshots or removal | `backend/core/career_exports.py`, `backend/api/platform.py` |
| Label insufficient, possibly truncated or repeated descriptions | `backend/core/description_quality.py` |
| Repair a snapshot into a separate reviewed JSON | `scripts/career/repair_export.py` |
| Change resume ranking or eligibility | `backend/core/matcher.py`, `match_sections.py`, `eligibility.py`, `experience.py` |
| Change the career JSON controls | `frontend/src/components/CareerExportPanel.tsx` |
| Change experience limits and bulk removal | `frontend/src/experience.ts`, `frontend/src/components/Sidebar.tsx`, `frontend/src/App.tsx` |
| Change the URL-reader controls | `frontend/src/components/UrlReaderPanel.tsx` |
| Change browser-site extraction | `url_reader/sources/` (including `indeed.py`) |
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
