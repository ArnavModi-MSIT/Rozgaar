# URL reader

Use the URL reader tab in Rozgaar, launched by `Start Rozgaar.cmd`. Use `Open Reader Chrome.cmd` to prepare the dedicated browser without collecting.

## Modules

- `url_reader/sources/`: site-specific search, listing and description extraction.
- `url_reader/browser/`: pagination, parallel detail workers, captured Wellfound search state.
- `url_reader/storage/`: checkpoint validation/atomic writes, seen-posting history and process locking.
- `url_reader/identity.py`: canonical posting IDs and source namespaces.
- `url_reader/quality.py`: description-quality evidence.
- `url_reader/engine.py`: orchestration, checkpoint resume, retries and CLI.
- `url_reader/supervisor.py`: bounded child-process watchdog and owned-tab cleanup.
- `url_reader/dashboard.py`: reader manager and optional standalone HTTP dashboard.

## Commands

From the repository root, run `runtime/python/Scripts/python.exe -m url_reader.engine --help`. The optional standalone dashboard is `runtime/python/Scripts/python.exe -m url_reader.dashboard --open`; daily use should use the combined platform.

`powershell -ExecutionPolicy Bypass -File scripts/open_reader_browser.ps1 -ChromeOnly` opens/reuses Chrome on loopback port 9222. Sign in or complete verification manually. Reader state lives in `runtime/reader/`, independently of career data.

For signed-in Wellfound `/jobs`, select filtered-tab mode and keep exactly one intended search open. Capture reuses that tab without reloading, scopes checkpoints by displayed filters, and verifies scope before committing jobs. Resume requires the same visible result batch. Signed-in descriptions and public JobPosting JSON-LD have separate extraction paths; empty required fields are not saved.

Wellfound filter capture supports native inputs and the site's collapsed button/combobox controls. It uses DOM order rather than screen coordinates, so sticky controls and scrolling do not alter the search identity. Saved/Hidden counters are excluded from that identity. Each posting ID in a company card is queued independently, including repeated title/Learn more links. Slow infinite-scroll results get an additional bounded wait; an idle scroll is not proof that all advertised results were collected.

To start Wellfound from a clean local collection history, stop the reader and run `runtime/python/Scripts/python.exe -m scripts.reset_wellfound` to preview, then add `--apply`. It removes active Wellfound checkpoints and source-specific seen rows from current/legacy history stores. Other sources, browser sign-in and settings are preserved. Recovery copies stay in ignored `.archive/`, outside the JSON importer.

A detail navigation timeout replaces the reader-owned tab before retry. The dashboard supervisor restarts once after 90 seconds without checkpoint progress, with extra allowance for long delays. A repeated stall keeps partial output and pending links. Stop terminates a stuck child after five seconds. Login/verification is not bypassed; only reader-owned tabs are cleaned up.

Original checkpoints remain immutable when the UI clarifies status messages. Five consecutive missing descriptions stop collection. Extraction-quality checks do not establish source completeness or candidate eligibility.

## Checks

Read-only inspection of the dedicated browser's visible search controls is available with `runtime/python/Scripts/python.exe -m url_reader.browser.wellfound_session --diagnose-search http://127.0.0.1:9222`. It does not navigate, change filters or start collection.

`runtime/python/Scripts/python.exe -m scripts.check --browser` runs unit/API tests and all intercepted browser fixtures. Fixture imports and supervised children use explicit package paths; test data never enters the real stores.

## Indeed

When an Indeed detail page blocks access, collection stops and leaves that tab open in the dedicated reader Chrome for manual verification. The watchdog also preserves this handed-off tab. Pending links remain in the checkpoint. If verification restores access, resume with one detail reader; if access remains denied, stop using the reader for that source. Verification and access restrictions are never bypassed.

Paste an HTTPS `in.indeed.com/jobs?...` URL, or use **Indeed: Dwarka / Delhi search** in the URL-reader panel. The preset retains the supplied Dwarka/Delhi location, salary, radius and opaque `sc` filter. Blank and repeated filters are preserved. `start`/`pp` pagination cursors and selected-job/tracking parameters are reset when beginning a search; they are not treated as filters.

Indeed has its own `indeed_*.json` checkpoints and `indeed` seen-history namespace. Card `data-jk` values and job/redirect links share the same strict 16-character job identity. Pagination uses the site's actual Next URL/control, preserving search filters. Full text comes from the scoped description or identity-matched public JobPosting data. Wrong-job redirects and empty descriptions are rejected. Login, HTTP 403/429 and verification pages stop collection for manual action. No Apply or Save action is automated.

`runtime/python/Scripts/python.exe -m tests.reader.indeed_browser_smoke` tests these paths with intercepted requests and synthetic data. It is included in `scripts.check --browser`; fixtures do not prove live access.
