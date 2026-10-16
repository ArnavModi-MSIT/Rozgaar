# Validation of supplied technical audits

**Implementation follow-up (October 16):** retention, common requirement headings, bare experience fields, active manual-skill preservation, conservative full-description/URL duplicate checks and model-safe atomic embedding caches are now implemented. Repeated parsing and snapshot fingerprints are cached. The findings and "unimplemented" statements below describe the earlier audit snapshot; see [README.md](../README.md) and [improvement.md](../improvement.md) for current behavior and verification.

October 16, 2026. Checked the local application runtime code corresponding to `f649ee6`, using the existing Windows virtual environment. This follows the [first audit comparison](ARCHITECTURE_AUDIT_REVIEW.md). Findings below distinguish reproductions, static inspection and estimates. Runtime source was not changed during this validation; the [roadmap](../improvement.md) records proposed fixes.

## Verification performed

- Offline suite: **291 tests passed**, reported test execution time **3.596 seconds**, with real **PyTorch 2.13.0+cpu** installed. FastAPI tests ran outside the restricted sandbox because its socket restrictions prevent TestClient startup.
- The ranking tests use synthetic data and fake encoders for determinism. Separately, the already-cached real `all-MiniLM-L6-v2` model encoded and ranked three synthetic jobs against one synthetic resume without downloading weights. Job vectors had shape `3 x 2 x 384`; resume vectors had shape `2 x 384`; scores were finite, including for a long description.
- Neither check establishes relevance accuracy, score calibration or fresher-parser precision/recall. No labeled benchmark was created and no production resume was used.
- Retention reproduction used an in-memory SQLite database. Benchmarks used generated text and a synthetic DataFrame. The existing job database and saved resume were not used or modified.
- No live collection or Linux CI run was performed.

The supplied review's **275 pass / 16 fail** result describes its environment with a stubbed torch dependency. It is not the result on this local Windows installation. Its cross-platform launcher concern remains valid.

## Reproduced defects

| Finding | Reproduction and impact | Location |
| --- | --- | --- |
| Cleanup uses creation age | A dismissed row with `first_seen` 400 days ago and `last_seen` today was deleted, along with a genuinely stale row; a recent row remained. Recollection can reset identity/dismissal. | `core/storage.py:cleanup_old` |
| Common headings remain general text | `Qualifications`, `Who you are`, `Key Requirements`, `What we're looking for` and `Skills required`, followed by Python/SQL, all populated `general` rather than `required`. `Required Qualifications` worked as the control. Required skills remain discoverable but lose their stronger weighting. | `core/match_sections.py:sections` |
| Bare experience fields lose their context | `Experience: 0-2 years`, `Experience: 1+ years` and `Experience: 5+ years` all returned `(None, None)` from `experience_requirements`. Controls `0-2 years of experience` and `1+ years of experience` returned minima 0 and 1. The current UI keeps unknowns, so experienced roles can pass this gate. | `core/experience.py`, `ui-react/src/App.tsx` |
| Shared description prefix collides | Two synthetic Data Analyst roles at one company/city, with more than 500 common opening characters but different Finance/Marketing responsibilities afterwards, produced equal dedup keys. | `core/dedup.py:dedup_key` |
| Windows-only behavior tests lack platform isolation | Simulating only the launcher's non-Windows guard caused two launcher-test errors and one stale-backend-test failure. This is a guard simulation on Windows, not a full Linux compatibility test. | `tests/test_launcher.py`, `tests/test_runtime_review.py`, `start.py:main` |

Fix retention and parsing first, each with regression tests. A labeled relevance dataset is necessary before model/weight changes, but need not delay deterministic correctness repairs.

## Performance: measured hot paths, not full-app latency

Synthetic description length: **3,327 characters**, with required Python/SQL qualifications and repeated analytics responsibilities. Three recognized skills were supplied. Each result is the median of five runs after two warmups; per-job methods ran 20 calls per run, and pool hashing ran once per run.

| Operation | Local median |
| --- | ---: |
| `weighted_skills` | 11.407 ms/job |
| `eligibility_checks` | 1.549 ms/job |
| `compute_job_pool_key` on 10,000 synthetic rows | 138.115 ms |

These numbers broadly support the review's concern about repeated regex/section work. Multiplying per-job cost by 10,000 is an extrapolation, not a measured request duration. Actual description distributions, skill vocabulary, hardware, cache state and job count determine runtime. No claim is made that the user's database currently contains 10,000 visible jobs.

Static inspection also confirms:

- `rescore()` holds the shared `RLock` while building embeddings, ranking and explanations. Job/resume data operations needing that lock wait. Saying it blocks **every endpoint** is too broad: `/api/runtime` and static content do not need this data lock. Upload work already runs in a thread pool; the shared-lock contention is a separate issue.
- List and detail payloads recompute the description-based pool fingerprint when a resume is loaded. Detail access can trigger a full rescore when the pool changed.
- `rank_by_resume()` creates eligibility explanations for every ranked job even though the explanation panel is displayed on expansion.
- `_load_jobs_df()` reads full rows and recomputes required/preferred experience on cache reload. Ingest stores the description-only minimum, while the API uses description plus numeric title evidence. API recomputation intentionally makes old rows follow parser corrections, but duplicates work and leaves the persisted field with different semantics.

Start with cached job-only features and per-snapshot fingerprints. Refactor scoring to compute from an immutable snapshot outside the lock and publish only when its version is still current. Any lazy explanation path must also track the current resume/job version. Avoid replacing the full-pool hash with an untracked counter that fails to notice collector writes from another process.

## Other claims requiring qualification

- **Relevance gate:** confirmed data/ML target-title bias in `config.TARGET_ROLE_RE` and the alternative 40% skill-overlap gate. This fits the current personal target roles but limits reuse for arbitrary fields. Make target roles configurable or resume-aware before presenting the matcher as general-purpose; do not simply remove the gate without evaluating unrelated-role false positives.
- **Freshness:** there is no verified open/closed status. Exact source-ID observations update `last_seen`; new IDs skipped by repost dedup do not refresh the matched record. Add provenance-aware observation tracking before relying on absence or reposts for lifecycle decisions.
- **Request conduct:** there is no shared per-host budget or robots-policy evaluator. Some adapters do set a User-Agent (`standard` uses `jobbot/1.0`), so “no User-Agent policy” is a consistency gap rather than proof every request lacks a header. Public page bootstrap tokens/nonces alone do not establish an access-control bypass; each adapter's actual access path needs separate assessment.
- **LinkedIn:** the general job-board feed is removed, but the employer-only guest-search adapter is still registered, always reports partial coverage and has no descriptions. README paragraphs saying simply “LinkedIn removed” conflict with its later employer-only explanation. Clarify the distinction; removing the employer source is a separate product decision.
- **Local API host checking:** the Origin guard rejects foreign-origin mutations when an Origin header is present; no Host allowlist is configured. Consider a loopback-host allowlist and explicit tests. The absence of an Origin header is also normal for local command-line clients; blocking all such requests is not an adequate substitute for Host validation. No DNS-rebinding exploit was reproduced here.
- **Documentation:** README has substantial dated source additions. Move those into dated source audits and keep setup, use, limitations and troubleshooting prominent.
- **Nightly live smoke tests:** useful as an optional maintenance workflow, with host limits and clear failures. They should not silently become scheduled scraping or make offline pull-request tests depend on external websites.

## Research and project reference checks

### Strongest direct methods to read

- [ConFit: Improving Resume-Job Matching using Data Augmentation and Contrastive Learning](https://arxiv.org/abs/2401.16349), Xiao Yu, Jinzhong Zhang and Zhou Yu, 2024. The authors use section paraphrases and contrastive training. The reported gains are on their datasets and tasks; they are not expected improvements for Job-Intel. A trained approach requires suitable labels/training and is not equivalent to the current section mean-pooling heuristic.
- [ConFit v2: Improving Resume-Job Matching using Hypothetical Resume Embedding and Runner-Up Hard-Negative Mining](https://arxiv.org/abs/2502.12361), Xiao Yu et al., 2025. Relevant for hard-negative sampling and domain adaptation. Generated reference resumes are research augmentation, not evidence of a real applicant's qualifications.
- [SkillSpan: Hard and Soft Skill Extraction from English Job Postings](https://aclanthology.org/2022.naacl-main.366/), Mike Zhang et al., NAACL 2022. The verified dataset contains 14.5K sentences and over 12.5K annotated spans. Useful for evaluating skill extraction; a dataset is not a drop-in replacement for the current 103-term vocabulary.
- [Efficient Text Encoders for Labor Market Analysis](https://arxiv.org/abs/2505.24640), Jens-Joris Decorte et al., 2025. This is the actual paper title behind the supplied Skill-XL/ConTeXT-match link; it introduces those methods/resources and JobBERT V2. Evaluate mapping, local runtime, licenses and vocabulary compatibility before reuse.

The linked [feature-fusion paper](https://arxiv.org/abs/2006.07017) and [interpretable classification/ranking paper](https://aclanthology.org/2021.icnlsp-1.15/) resolve to relevant person-job-fit titles. The three supplied survey links also resolve to the stated subject areas: [talent analytics](https://arxiv.org/abs/2307.03195), [job recommender systems](https://arxiv.org/abs/2111.13576) and [e-recruitment challenges](https://arxiv.org/abs/2209.05112). This check verified their identity and scope, not every cited experiment. The SkiLLMo repository page could not be retrieved in this check.

### Project claims

- [JobSpy](https://github.com/speedyapply/JobSpy) exists and supports multiple job-board adapters. Star counts are volatile and irrelevant to local correctness. Its availability does not establish that our own employer adapters work or justify adding back removed feeds.
- “Apify ATS scrapers are commercial, not open source” is too broad. Commercial hosting and open-source code can coexist: [this ATS aggregator](https://github.com/wickfeed/ats-job-aggregator) has a [public MIT license](https://github.com/wickfeed/ats-job-aggregator/blob/main/LICENSE). This is a license counterexample, not a runtime quality review or a recommendation to adopt the service.
- A limited literature search cannot establish that no research addresses India fresher eligibility. Treat an India-specific labeled eligibility benchmark as a potentially useful contribution, not a verified novelty claim.

## Recommended implementation order

1. Correct cleanup retention, bare experience fields and heading aliases; add focused regressions.
2. Create private or shareable synthetic labels for relevance and separate hand-reviewed eligibility examples. Compare BM25, MiniLM-only and hybrid on identical held-out sets; report precision@10 and NDCG@10, plus experience extraction errors.
3. Cache job-only matching features, remove repeated snapshot hashing and reduce scoring lock duration, preserving invalidation and custom skills.
4. Add model-aware job-cache validity, safe duplicate provenance, per-company completeness and explicit lifecycle states.
5. Add offline CI with Windows launcher coverage, then opt into bounded live source maintenance if wanted.

This validation changed documentation only. Proposed fixes remain unimplemented and were not pushed.

## Third supplied audit: additional checks and corrections

The third review was based on an extracted snapshot and could not run tests or browse. Its grades and file-count estimates are opinions/snapshot observations, not measured quality results. The following checks use the current source-only checkout and installed dependencies; no runtime code was changed.

### Code claims checked

| Claim in third review | Result |
| --- | --- |
| Custom skill strings are compiled without escaping; C++ is broken | **False.** `core/skills.py:build_patterns` already applies `re.escape(skill)` and punctuation-aware boundaries. Literal checks for C++, C#, `a.b`, `python\|sql`, `[abc]`, `(test)` and `a*` passed. No escaping fix is needed. |
| Company test filenames imply live scraping | **Unsupported and contradicted by execution.** The cited batch/fifteen-source tests patch HTTP helpers with inline JSON/HTML fixtures. All **291 tests passed in 3.852 seconds** with unmocked `requests.Session.request` and `urllib.request.urlopen` calls rejected; there were **zero** such transport attempts. Local ASGI TestClient operation was allowed. |
| Missing pytest prevents running the suite | **False for this repo.** Tests use `unittest`; run `python -m unittest discover -s tests -v`. A pytest conversion or `conftest.py` is optional, not a prerequisite for CI. |
| `embed_jobs()` is dead code | **False.** `rank_by_resume()` calls it when embeddings are not supplied. This is also the evaluation script's default path. The application API uses the incremental cached path. |
| Long resumes are still truncated at the embedding token limit | **Not supported by current matcher code.** Selected section text is tokenized with `truncation=False`, split into 192-token chunks, then pooled. Section recognition, PDF reading order and pooling quality are separate evaluation gaps. |
| CMD launchers have fixed absolute checkout paths | **False.** Both derive paths from `%~dp0` and support organized/flat layouts. `start.py` remains intentionally Windows-only; its test portability issue is recorded above. |
| Jobs table has no secondary indexes | **Confirmed.** `PRAGMA index_list('jobs')` in a fresh in-memory schema showed only `sqlite_autoindex_jobs_1`. Choose new indexes from measured query plans. |
| Cleanup should run in the API as well | **Reject this recommendation.** Cleanup currently runs after collection or via its explicit CLI command. Running destructive retention during UI reads is unnecessary; repair its `first_seen` policy first. |
| Batch audit JSON belongs under docs | **Already true for the named example.** `COMPANY_BATCH_OCT15.json` is in `docs/`. Some legacy audit/inventory files remain at application root; that is an organization task, not a parsing defect. |
| Dependency versions, CI and Python lint gates are missing | **Confirmed.** Python requirements are bare names; there is no GitHub Actions workflow or Python lint configuration. React already has a lockfile and a TypeScript compiler build. |

The transport-blocked test run verifies the collectors' requests/urllib paths did not make live calls in this suite. It is not a universal network-isolation guarantee for every possible future library. Fixture quality and upstream schema drift still require maintenance; a single file under `tests/fixtures/` does not mean inline response fixtures are absent.

### Recommendations worth keeping, with limits

- Keep the labeled relevance/eligibility evaluation, dependency locking, offline CI and cautious lifecycle status work. Fix the already reproduced retention/experience/heading defects before expanding infrastructure.
- A full-history dedup preload is a full scan even if an index on `source` exists. Store a corrected/versioned fingerprint or maintain canonical groups only after evaluating false merges; hashing the current prefix does not repair its collisions.
- Share request/ATS contracts where appropriate. Consolidating every employer into one large dispatcher or targeting fewer than 15 custom files does not itself improve maintainability.
- Do not hide a job solely because the title says Senior, Lead or Analyst III. Preserve the user's description-based experience policy; explicit numeric evidence and unknown handling need tests.
- Add real authentication before any multi-user/network deployment. The existing Origin guard is a browser mutation check, not authentication. Missing Origin on a normal local CLI request is not itself evidence of a vulnerability.
- Bulk-dismiss input limits, extracted-text privacy checks, optional OCR and focused React interaction tests are reasonable bounded improvements. This review did not reproduce an attack, privacy leak or React rendering defect.
- Do not adopt a new skill model or fine-tune merely because a paper reports better results. The available label volume, dataset split, license, local hardware and held-out scores determine whether it helps this project.

### Reference corrections verified online

1. **Open Job Description is the wrong domain.** Its official [specification](https://github.com/OpenJobDescription/openjd-specifications) defines portable batch-processing/render jobs, not employment vacancies. Do not use it as a hiring schema. For employment interchange, [Schema.org JobPosting](https://schema.org/JobPosting) is a relevant reference; the internal collector contract can remain a smaller validated schema.
2. **The Resume Matcher repository attribution is wrong.** The identifiable project is [srbhr/Resume-Matcher](https://github.com/srbhr/Resume-Matcher). Its current public description is an AI resume-building/tailoring tool; the review's YAKE/TextRank implementation claim was not verified against a pinned code revision and should not be used as a dependency decision.
3. **The Zhu et al. venue is wrong.** [Person-Job Fit: Adapting the Right Talent for the Right Job with Joint Representation Learning](https://arxiv.org/abs/1810.04040) is a real paper; the [author institution's publication record](https://www.researchwithrutgers.org/en/publications/person-job-fit-adapting-the-right-talent-for-the-right-job-with-j/) identifies **ACM Transactions on Management Information Systems**, 2018, DOI `10.1145/3234465`, not ACM TIST.
4. **The sparse-interaction citation is misattributed.** The verified title is [Learning to Match Jobs with Resumes from Sparse Interaction Data using Multi-View Co-Teaching Network](https://arxiv.org/abs/2009.13299), **Shuqing Bian et al., CIKM 2020**, not Zhang et al., WSDM 2020. Its method uses sparse/noisy interaction data; that is not equivalent to this application's absence of interaction training data.
5. **Sentence-BERT is background methodology, not the exact checkpoint name.** The code uses `sentence-transformers/all-MiniLM-L6-v2`. The SBERT paper does not validate the current score constants or demonstrate that a small fine-tuning set will necessarily beat this hybrid.

The remaining loosely named workshop/challenge/Job2Vec references were not established as precise publications here. The conclusion that fine-tuning on a small set necessarily beats heuristic blending is unsupported for this repo. Keep those as research leads until exact sources and comparable evaluation results exist.

**Result:** retain the confirmed reproducibility/indexing/maintenance ideas, reject the false bug reports, and preserve the correctness-first implementation order in the roadmap. These checks added documentation only; proposed runtime fixes are still unimplemented and unpushed.

## Fourth supplied audit: new evidence and policy distinction

The fourth review accurately distinguishes configuration counts from verified coverage and heuristic scores from evaluated recommendation quality. Its cache identity, prefix deduplication, nested concurrency, lifecycle and evaluation findings largely repeat the verified backlog. A cooperative deadline does not forcibly cancel blocked operations; the current thread executor also waits for workers when leaving its context. Treat per-request timeouts and deadline propagation as part of the host-budget work, not as a proven hard wall-clock limit.

### New reproduced defect: active manual skills are replaced

Both `api/main.py:create_custom_skill` and `delete_custom_skill` re-extract resume skills and call `data.set_resume()` without consulting the saved per-resume override. A temporary SQLite database and synthetic resume reproduced this behavior; only rescoring was patched out to isolate handler state changes:

| Step | Effective skills |
| --- | --- |
| Synthetic resume text | `Python and SQL analyst` |
| User's saved and active correction | `python`, `power bi` (SQL deliberately removed) |
| Add global custom skill `analyst` | Active set becomes `analyst`, `python`, `sql` |
| Restore correction, then delete global custom skill `analyst` | Active set becomes `python`, `sql` |
| Read SQLite override afterwards | Still `python`, `power bi` |

This is an **active-state consistency bug**, not permanent deletion of the stored correction. The React app has no global custom-skill controls, so the immediate trigger is API use. Reuse resume activation's full-set override precedence, including empty overrides, and test add/delete/reload consistency. No production resume or database was used.

### Preferred experience: an explicit filter-policy choice

The review correctly describes the calculation: the current filter checks the maximum of required/preferred minima. The React label explicitly says **Hide 1+ years required or preferred**, and the bulk-dismiss label uses the same policy. A required minimum of zero plus a preferred minimum of two is therefore hidden when this filter is on.

Required-only filtering is a useful alternative because a preference need not establish ineligibility. However, switching to it changes the current strict policy. Offer a distinct required-only mode if wanted, retaining separate evidence and a clear label; do not silently change the default or claim that preferred experience is a mandatory employer requirement. Mixed fresher/senior tracks still need explicit evidence, not an assumed zero minimum.

The relevance-gate concern is also plausible, not a demonstrated misranking of the example occupations. Test configurable role preference and low-score visibility against labeled adjacent and unrelated roles before changing the gate or its current 20-point UI cutoff.

### Research references verified

- [BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models](https://arxiv.org/abs/2104.08663), 2021, is a real retrieval benchmark. It supports comparing lexical/dense/reranking methods across tasks; it does not supply Job-Intel-specific relevance labels or guarantee hybrid improvement.
- [ConFit v2](https://aclanthology.org/2025.findings-acl.661/) has a verified Findings of ACL 2025 publication, DOI `10.18653/v1/2025.findings-acl.661`, in addition to the previously checked arXiv version. Treat its supervised/domain-adapted training as an experiment after establishing a benchmark.
- [M3-Embedding / BGE-M3](https://arxiv.org/abs/2402.03216), 2024, is a real multilingual model covering dense, sparse and multi-vector representations. Benchmark its quality, memory and CPU latency locally before considering replacement of MiniLM; no model was installed by this validation.
- [SQLite FTS5](https://www.sqlite.org/fts5.html) provides full-text search and BM25 ranking, making it a relevant local lexical-retrieval experiment. Combining retrieval systems still needs score/rank fusion, filtering and cache/index invalidation tests.
- [JobFunnel](https://github.com/PaulMcInnis/JobFunnel) was archived on December 10, 2025. Its documented CSV status workflow includes interested/applied/interview/offer and rejected/archive states. This is a workflow reference, not evidence that its old collectors still work. No JobFunnel runtime was tested.
- The project named only **Job Recommendation** cannot be uniquely identified from the supplied text; no exact repository URL was provided. Its implementation and comparison claims remain unverified.

For an ESCO experiment, use a versioned local taxonomy snapshot and verify occupation/skill mappings on India roles. A hosted taxonomy lookup during matching is unnecessary for this local project. Recall@50 requires a sufficiently large candidate pool and adequate relevance judgments; an incompletely labeled live pool does not establish full recall.

### Verification limits and revised order

The review's 288-pass/one-failure adjusted run used substituted ML dependencies and excluded Windows tests. That does not supersede the real-dependency Windows checks recorded above: 291 passing tests, the small real-model smoke check, and the separate 291-test requests/urllib transport-blocked run. Those runs establish tested behavior, not recommendation accuracy. No full-suite rerun was needed for this documentation-only comparison; the new API state issue was isolated separately.

Keep the current priority: retention, experience/heading parsing and active manual skill preservation; then labeled relevance/eligibility evaluation and measured scoring improvements; then source completeness, safe provenance/lifecycle, model-safe caches and CI. Required-only experience mode and a BM25/dense/top-N reranker are explicit product/research options. The four-week schedule in the supplied review is a proposed plan, not an effort estimate verified against this codebase.

This comparison updated documentation only. No runtime fix, model swap, filter-policy change or push was performed.
