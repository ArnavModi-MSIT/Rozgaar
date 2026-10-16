# Matching evaluation

The live ranker is still the current local MiniLM + weighted-skills heuristic. This update does not claim better accuracy from changed weights or introduce a new ranking model.

## Make a meaningful comparison

1. Copy `examples/matcher_synthetic.json` to ignored `db/my-match-labels.json`.
2. Replace its resume and jobs with a representative set. Set `synthetic` to false. Include good matches, adjacent roles, shared-skill false positives, incomplete descriptions and unknown eligibility. Use unique string IDs and at least 30 jobs; a larger varied set is better.
3. Before looking at rankings, grade relevance: 0 poor, 1 partial, 2 good. Score required experience/location/student eligibility separately. A senior data engineer may be relevant to data work while being ineligible for a fresher.
4. Keep a separate holdout file that you do not use for choosing weights.
5. Run `python scripts/evaluate_matcher.py db/my-match-labels.json --k 10 --output db/my-match-report.json`.

No dataset is exported from your active resume automatically. The evaluator writes no job DB or embedding cache. Input/report files under `db/` are ignored by Git. Reports include posting IDs and aggregate metrics, not resume text or JDs. Review them before sharing.

## What it compares

- **BM25:** an in-memory SQLite FTS5 index, title weight 2 and description weight 1; an OR query of up to 256 sorted unique non-stopword resume tokens. HTML is stripped. Every job is retained; unmatched jobs sort last, with ID ties. This is a fixed reproducible lexical baseline, not a tuned production search engine. SQLite's score sorts with lower values first. [Official FTS5 documentation](https://www.sqlite.org/fts5.html#the_bm25_function).
- **MiniLM sections only:** the same section embeddings as the live ranker, with raw cosine similarity; requirements/responsibilities weighted 55/45 when resume evidence exists. No weighted skills, fixed score scaling or target-role gate.
- **Current hybrid:** exactly `core.matcher.rank_by_resume` with the same precomputed job/resume vectors. Eligibility explanations are disabled for ranking timing. Inputs are sorted by ID so ties remain deterministic across methods.

Precision@k counts grade-2 jobs among the first k (or all jobs when fewer exist). NDCG@k uses graded gains `2^grade - 1` and the same pool's ideal ordering. Reported encoding time includes model startup; per-method ranking times exclude the shared encoding. BM25 timing includes its in-memory index build. Compare warm and cold full-app timing separately if latency is the question.

## Verification on October 16

The real already-cached MiniLM model ran all three methods on the included 18-job synthetic sample at k=5. BM25 precision/NDCG were 0.8 / 0.913; section MiniLM and the current hybrid were both 1.0 / 1.0. These easy constructed examples do **not** establish recommendation accuracy or justify changing the live weights. The private full report remains in ignored `db/matcher-evaluation.json`.

The API now skips per-job eligibility checks during whole-pool ranking and adds them on details/Why this ranking expansion. Unit/API and browser checks verify evidence still appears and ranking scores are unchanged. Full-pool scoring remains synchronized with resume state; lock-free background ranking is not part of this change.
