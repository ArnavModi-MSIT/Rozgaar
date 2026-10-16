# Improvement roadmap

Updated October 16, 2026. Job Intel is a personal, local application. Favor fewer missed opportunities, useful filters and quick repeat use. Add features only when they solve an observed problem.

## Completed in this implementation

- **Experience parsing:** numeric-only Experience fields, required/preferred field labels, HTML boundaries and Unicode ranges work. Zero-based ranges remain distinct from unknowns and 1+ minima.
- **Requirement headings:** Qualifications, Who you are, Key Requirements, What we're looking for and Skills required are recognized. Preferred sections stay separate.
- **Manual skills:** global custom-skill edits preserve the saved full-set resume correction, including an empty set. No-op edits skip rescoring; automatic profiles update when there is no correction.
- **Retention:** cleanup uses `last_seen`, with a legacy `first_seen` fallback, preserving recently observed old jobs and dismissals.
- **Conservative deduplication:** full normalized descriptions and canonical posting URLs replace the shared 500-character prefix. Distinct URLs and incomplete descriptions remain separate. Confirmed duplicates refresh observation dates without resetting dismissals.
- **Embedding-cache safety:** shared model/parser/chunk signatures, finite/shape validation, atomic writes and a nonfatal disk-cache failure path. Old vectors rebuild once after updating.
- **Repeat-use speed:** bounded caches reuse job skill sections and experience results; the job snapshot stores its fingerprint once instead of hashing full descriptions on every list/detail click.

No additional service, cloud API, database schema or model was introduced. The existing local saved-resume feature, MiniLM matcher and strict required-or-preferred 1+ experience filter remain in use.

### Verification

Offline unit/API tests cover these failures, unchanged-job cache reuse, model/parser changes, malformed vectors, interrupted writes, saved-resume reload and manual corrections. A separate smoke check uses the real already-cached MiniLM model with synthetic jobs/resume. These checks establish behavior, not measured recommendation accuracy. The per-step synthetic skill-cache benchmark is not a full-app speed benchmark.

Close the previous API console, then launch **Open Job Intel.cmd**. Existing descriptions are re-evaluated on API reload. A later normal collection is needed to recover postings skipped by the former dedup policy. The more conservative rule can show genuine reposts with new URLs separately; that tradeoff avoids silently losing distinct openings.

## Next useful local improvements

### 1. Make removed jobs easy to recover

- Add undo for a removal and a view of dismissed jobs.
- Add lightweight saved/applied states only if useful to the daily workflow.
- Keep original links, notes and dates in the existing SQLite database.

**Success:** a mistaken removal is recoverable from the UI and application progress survives a restart.

### 2. Show source problems clearly

- Extend existing `stats.py --health` information with per-company counts, missing descriptions and complete/partial/failure reasons.
- Expose a compact health view through the existing API and UI when it is useful; a separate metrics service is unnecessary.
- Coordinate requests to shared ATS hosts, honor date/numeric Retry-After values and report cooldowns/partial results explicitly.
- Consume completed collection results promptly while keeping SQLite writes sequential.

**Success:** a broken or incomplete company source is obvious without reading a long traceback.

### 3. Improve freshness without hiding valid jobs

- Show the latest observation/check date clearly.
- Add open/closed/unknown only when a source gives reliable evidence. A failed or partial run must not close its jobs.
- Preserve source IDs and user state. Consider duplicate relationships only if visible duplicates become a practical problem; no learned deduplication system is needed by default.

**Success:** confirmed closed jobs leave the default list while temporary source failures preserve existing opportunities.

### 4. Improve matching from actual mistakes

- Hand-review a small representative set of relevant, borderline and irrelevant jobs, including adjacent roles and overlapping-skill false positives.
- For numerical comparisons, keep held-out labels private and compare BM25, MiniLM-only and the current hybrid on identical data. The existing evaluator reports precision and NDCG; do not invent results.
- Experiment with SQLite FTS5/BM25 or a local top-N reranker only if the baseline shows a need and local latency is acceptable.
- Make required-only experience filtering or role-preference controls explicit options if wanted. Keep the current strict filter as the existing default.
- Inspect difficult PDF extraction and scanned resumes. Optional local OCR should run only when needed and show the extracted text for review.

**Success:** changes address reviewed errors and preserve useful fresher opportunities. A larger model is not automatically an improvement.

### 5. Keep maintenance practical

- Record tested Python/dependency versions so updates are repeatable; React already has a lockfile.
- Fix Windows-specific test isolation before adding cross-platform CI. Use the existing offline unittest suite and React build; pytest conversion is optional.
- Add SQLite indexes only after checking actual queries; use ordered migrations when the next schema change is needed.
- Share common ATS/request helpers where contracts match, preserving employer-specific country and detail rules.
- Simplify README/config prose as those areas are touched. Keep source audits in docs.

## Remaining limits

Scoring still uses the shared API state lock, explanations are generated for the full ranked pool, and ranking constants are uncalibrated. Source completeness varies and postings do not yet have a verified lifecycle state. Those are remaining improvements, not completed features.

Celery/Redis, Kafka, Kubernetes, a separate vector database, multi-user hosting and LLM agents are outside the current local-use plan.

## Review evidence

- [Initial audit comparison](docs/ARCHITECTURE_AUDIT_REVIEW.md)
- [Consolidated audit validation](docs/AUDIT_VALIDATION_OCT16.md)
- [Current architecture](ARCHITECTURE.md)
