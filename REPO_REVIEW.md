# Repository review — 2026-10-07

## Completed

- Organized the local workspace into outer CMD launchers, app/ and the preserved virtual environment. Original Git history, jobs database, embedding cache and user state were preserved. Database/cache SHA-256 checks were unchanged across the move.
- Removed obsolete debug log, two captured Microsoft page assets, and legacy UI/Python cache clutter. Maintained useful debug scripts inside app/debug/.
- Fixed independent experience requirements, decimal years, preferred-only semantic text and ambiguous graduation ranges.
- Removed remaining Lever/Ashby description truncation, refreshed Deloitte content, and repaired refetch enrichment resets.
- Committed collection writes per source, prevented overlapping collectors, and checked standard-board deadlines before queued work starts.
- Anchored database paths to source files. Launchers now check backend checkout/revision and support organized or flat layouts.
- Synchronized resume state, restored prior state on failed upload scoring, and refresh scores on changed job content/skills/locations/IDs. Schema initialization is once per database per process.
- Refreshed resume-dependent detail panels, cleared retry errors, and guarded busy controls.
- Rejected unexpected browser origins for mutations and corrected upload response shape.
- Patched source-map-js in the lockfile.

## Verification

- 162 offline Python tests passed after the move.
- Python compileall passed.
- npm ci and production React build passed.
- npm audit: zero reported advisories at review time.
- pip check: no broken installed requirements.
- Both outer CMD launchers passed --check without starting services or collection.
- API, experience payload, origin guard, dismissal and built-site integration passed against temporary data.
- Tracked source export contains no database/cache/dependencies or matching credential patterns; this is not a full-history secret audit.

## Limits

This review covered local source, pipeline/storage/API/UI contracts, launch paths and dependency advisories. It did not run every external career site or certify complete live coverage. Sites and terms can change; historical audits remain dated snapshots.

Experience and eligibility remain heuristic: mixed tracks, unusual headings and incomplete older source descriptions still need review. A local score is relevance, not an eligibility/hiring probability. The matcher needs user-labeled ranking evaluation.

The app remains a localhost single-user prototype without authentication or multi-user isolation. A collection deadline stops queued boards but does not forcibly interrupt an already-running HTTP request. Existing virtual environment entrypoints remain bound to the original outer path.

No model/resume data, SQLite files, installed dependencies or build output are included in the source-only GitHub sync.
