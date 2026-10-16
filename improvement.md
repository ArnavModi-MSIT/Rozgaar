# Improvement roadmap

Updated October 16, 2026. This is a personal local app. Prioritize daily usability and fewer missed opportunities.

## Implemented

- Experience parsing handles numeric-only fields, required/preferred labels, HTML boundaries and Unicode ranges. Ranges starting at zero remain distinct from unknown and 1+ minima.
- Common requirement headings and full descriptions are retained. Manual skill corrections survive global vocabulary edits, including an empty corrected set.
- Deduplication uses full descriptions and canonical posting URLs. Distinct URLs or incomplete descriptions are kept; confirmed duplicates refresh observation dates without resetting user state.
- Atomic embedding caches validate parser/model identity, shape and finite values. Repeated job features and snapshot fingerprints are cached; saved resumes can reuse parsed text and vectors.
- **Recovery/tracking:** Undo and paginated Removed history, mutually exclusive Saved/Applied states, private notes and dates. Tracker views bypass discovery filters. Retention preserves tracked jobs and notes.
- **Health/status:** searchable company/source outcomes and missing-JD counts, with explicitly unverified company completeness for older adapters. New feed observations show open in feed, legacy jobs start unknown, and a manual reviewed closure hides a job. Failed/partial/empty runs never infer closure or overwrite a user's closed mark.
- **Matcher evaluation/speed:** BM25, MiniLM sections and the hybrid are compared on identical labels. Synthetic example included; real accuracy needs representative private labels. Eligibility checks run on card expansion instead of for the entire ranked pool. Scores and weights remain unchanged.
- **Maintenance:** Windows/Python 3.10.11 dependency lock, scoped lock generator, SQLite visible-date/history indexes and Windows CI for network-guarded offline tests plus the locked React build.

## Still useful, when evidence warrants it

1. **Human matching labels:** review at least 30 varied real jobs and retain a separate holdout set. Use `scripts/evaluate_matcher.py` before changing weights or adding a reranker. The synthetic sample is not accuracy validation.
2. **More board-level health metadata:** standard Greenhouse/Lever/Ashby and employer-portal adapters report per-company outcomes. Other successful adapters explicitly remain unverified at company level. Extend those contracts when diagnosing a real source issue.
3. **Verified closure automation:** add individual ATS closure signals only when reliable. Current closure is manual; feed observations do not independently prove an application is open. Never infer closure from missing jobs or network errors.
4. **Shared-host request coordination:** improve fairness/cooldowns where rate limits are observed and consume completed platform futures promptly, preserving sequential SQLite writes. Do not add queues/services by default.
5. **Difficult resume extraction:** inspect actual PDFs before adding optional local OCR. Offer extracted text for review if layout mistakes recur.
6. **Scoring latency:** scoring still holds the shared state lock; cheap component explanations remain per-pool while eligibility is lazy. Measure real delays before adding generation-safe background scoring or changing models.

No Redis/Celery, separate vector database, paid APIs, hosted runtime or multi-user system is needed for the current project.

## Verification and limits

Offline tests and real cached-model synthetic checks verify behavior, cache reuse and evaluator operation. Browser checks use synthetic jobs/resume and a temporary database. Live company counts and completeness need a later normal collection. CI configuration is versioned; the actual hosted run status must be checked after pushing.

- [Architecture](ARCHITECTURE.md)
- [Matching evaluation](docs/MATCHER_EVALUATION.md)
- [Earlier audit validation](docs/AUDIT_VALIDATION_OCT16.md)
