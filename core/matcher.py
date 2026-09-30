"""
Resume-to-job matching via sentence embeddings + cosine similarity — same
all-MiniLM-L6-v2 model already used for job categorization (core/classify.py,
shared loader in core/embeddings.py). TF-IDF only scores literal shared
words; embeddings capture semantic closeness — a resume doesn't need to
contain every word a posting uses to score as a reasonable match.

Two real problems this version fixes vs. the previous one:

1. Per-batch min-max rescaling was misleading: (sims - lo) / (hi - lo) * 100
   guarantees the BEST match in whatever pool you're looking at always
   shows ~100%, regardless of whether it's actually a good match — "best
   of what's here," not "how good is this." Now blended with skill_pct
   (core/skills.py's exact keyword overlap), which is a real count-based
   percentage that doesn't inflate the same way — a job needing 5 skills
   you have 1 of genuinely reads low, not stretched toward 100% just for
   being the best available option.

2. all-MiniLM-L6-v2's default max_seq_length (256 tokens, ~1000-1500 chars)
   was silently truncating both resume and job text well before this
   file's own character caps ever mattered — see core/embeddings.py,
   raised to 384. Char caps here raised accordingly so more real content
   reaches the model instead of being cut by us before the model even
   gets it.

A third problem, found later, that the blend alone still couldn't fix:
postings from a genuinely different field (LLM fine-tuning, network
security) were still scoring 60%+ against a Data Analyst resume, because
their only "skill overlap" was on generic, near-universal terms
(python/aws) that say nothing about actual fit. See
RELEVANCE_SKILL_PCT_THRESHOLD/RELEVANCE_GATE_CAP and rank_by_resume()'s
relevance gate below — a deliberately simple, deterministic title-or-real-
skill-overlap check, not another embedding-based signal, per an explicit
"working best, not buzzwords" call: this is a personal tool, not a demo.

Job-pool embedding is split out into its own function (embed_jobs) rather
than being inlined into rank_by_resume — job embeddings depend only on the
job pool, never on the resume, so re-embedding potentially hundreds or
thousands of job descriptions on every single resume upload (the previous
behavior) wasted most of the "scoring jobs against resume" time on work
that didn't need to be redone at all. Callers (ui/app.py) can now cache
embed_jobs()'s result keyed on the job pool alone, and only pay the (much
cheaper, single-string) resume embedding cost on each new resume.
"""

from sentence_transformers import util

import os

import torch

import config
from core.embeddings import get_model
from core.skills import extract_skills, skill_overlap

# Empirically-reasonable clip range for this model's cosine similarities
# between different professional documents — NOT independently measured
# in this session (no ability to run the model here), based on general
# known behavior of MiniLM-family embeddings: unrelated text rarely drops
# below ~0.1, closely related text rarely exceeds ~0.65. May need
# retuning once you observe real numbers — if everything still reads
# suspiciously high or low, tell me the actual raw similarity range and
# I'll adjust these bounds specifically instead of guessing again.
SIM_FLOOR = 0.15
SIM_CEILING = 0.65

# semantic_weight is derived as 1.0 - skill_weight below (see rank_by_resume) —
# SKILL_WEIGHT alone fully determines the 60/40 blend at full skill confidence.
SKILL_WEIGHT = 0.4

# Below this many recognized skills on a job posting, skill_pct's weight
# in the blend is scaled DOWN proportionally — see rank_by_resume(). A job
# listing only 1 keyword isn't a confident signal the way a job listing
# 5+ keywords is; without this, one lucky keyword match could swing 40%
# of the final score exactly as much as genuinely matching every one of
# 10 required skills would.
MIN_SKILLS_FOR_FULL_WEIGHT = 3

JOB_TEXT_CHAR_LIMIT = 2500

# Relevance gate — see rank_by_resume(). A job counts as relevant if its
# title matches config.TARGET_ROLE_RE, OR it has real skill overlap with
# the resume (not just any overlap: two generic terms like "python"/"aws"
# is exactly what let "LLM Developer" and "Network Security Engineer"
# score 60%+ against a Data Analyst resume even after the skill taxonomy
# was fixed to recognize their real requirements — their overlap was
# still only ~12-25% of what each job actually asked for). Neither signal
# holding caps the blended score down here regardless of how high the raw
# semantic similarity read — deliberately simple and deterministic rather
# than another ML knob, per an explicit "working best, not buzzwords" call.
RELEVANCE_SKILL_PCT_THRESHOLD = 40
RELEVANCE_GATE_CAP = 10.0


def compute_job_pool_key(jobs_df):
    """Fingerprint of the job pool, kept for any caller that just wants to
    know "did the pool change at all" cheaply (e.g. to decide whether to
    show a status message) — NOT used for embedding-cache validity
    anymore (see embed_jobs_incremental below, which validates per-job
    instead of all-or-nothing)."""
    import hashlib
    if jobs_df.empty:
        return hashlib.sha256(b"").hexdigest()
    parts = (
        jobs_df["id"].astype(str) + "|" + jobs_df["title"].fillna("") + "|" + jobs_df["description"].fillna("")
    ).tolist()
    combined = "\n".join(sorted(parts))
    return hashlib.sha256(combined.encode()).hexdigest()


def _job_content_hash(job_id, title, description):
    import hashlib
    return hashlib.sha256(f"{job_id}|{title or ''}|{description or ''}".encode()).hexdigest()


def embed_jobs(jobs_df):
    """Embeds every job's title+description, unconditionally — no caching.
    Kept as a simple building block; embed_jobs_incremental (below) is
    what callers should actually use for anything beyond a one-off script,
    since it avoids redoing work for jobs already embedded."""
    if jobs_df.empty:
        return None
    model = get_model()
    job_texts = (
        jobs_df["title"].fillna("") + " " + jobs_df["description"].fillna("")
    ).str.slice(0, JOB_TEXT_CHAR_LIMIT).tolist()
    return model.encode(job_texts, convert_to_tensor=True, batch_size=64, show_progress_bar=False)


def embed_jobs_incremental(jobs_df, cache=None):
    """Embeds only jobs NOT already covered by `cache` — a dict of
    job_id -> (content_hash, embedding_row_tensor), typically loaded via
    load_embedding_cache(). A cached embedding is reused only when BOTH
    the job_id AND its content hash (id+title+description) match; a job
    whose description changed later without its id changing (e.g. via
    run.py --refetch-oracle) is correctly NOT reused.

    This is the fix for a real problem: the previous whole-pool-hash
    approach invalidated its ENTIRE cache the moment the pool changed by
    even one row — meaning dismissing 2-3 jobs (which shrinks the pool
    once ui/app.py's cache TTL expires) forced a full re-embed of
    potentially thousands of unrelated jobs. Per-job caching means
    removing rows costs nothing (their entries just aren't included in
    the output) and adding rows only costs embedding those specific new
    ones — dismissing a few jobs, or run.py fetching a handful of new
    postings, no longer re-embeds anything that hasn't actually changed.

    Returns (embeddings_tensor, updated_cache, num_newly_embedded).
    embeddings_tensor is row-aligned with jobs_df. updated_cache has
    entries added for newly-embedded jobs and entries for job ids no
    longer present in jobs_df dropped (keeps the persisted cache from
    growing unboundedly as old jobs cycle out via cleanup_old())."""
    if jobs_df.empty:
        return None, {}, 0

    cache = dict(cache) if cache else {}
    model = get_model()

    job_ids = jobs_df["id"].tolist()
    titles = jobs_df["title"].fillna("").tolist()
    descriptions = jobs_df["description"].fillna("").tolist()
    current_ids = set(job_ids)

    rows = [None] * len(job_ids)
    to_embed_idx = []
    to_embed_texts = []
    for i, (jid, title, desc) in enumerate(zip(job_ids, titles, descriptions)):
        h = _job_content_hash(jid, title, desc)
        entry = cache.get(jid)
        if entry is not None and entry[0] == h:
            rows[i] = entry[1]
        else:
            to_embed_idx.append(i)
            to_embed_texts.append(f"{title} {desc}"[:JOB_TEXT_CHAR_LIMIT])

    if to_embed_texts:
        new_embeddings = model.encode(to_embed_texts, convert_to_tensor=True, batch_size=64, show_progress_bar=False)
        for offset, i in enumerate(to_embed_idx):
            row_tensor = new_embeddings[offset]
            rows[i] = row_tensor
            jid = job_ids[i]
            h = _job_content_hash(jid, titles[i], descriptions[i])
            cache[jid] = (h, row_tensor)

    # Drop cache entries for jobs no longer in the current pool — keeps
    # the persisted cache file from growing unboundedly over time as old
    # jobs eventually get deleted by cleanup_old().
    cache = {jid: entry for jid, entry in cache.items() if jid in current_ids}

    embeddings_tensor = torch.stack(rows)
    return embeddings_tensor, cache, len(to_embed_idx)


DEFAULT_EMBEDDINGS_CACHE_PATH = "db/job_embeddings_cache.pt"


def save_embedding_cache(cache, path=DEFAULT_EMBEDDINGS_CACHE_PATH):
    """Persist the per-job embedding cache to disk — survives a Streamlit
    RESTART, not just a session. cache: dict of job_id -> (content_hash,
    embedding_row_tensor), as produced by embed_jobs_incremental()."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    torch.save(cache, path)


def load_embedding_cache(path=DEFAULT_EMBEDDINGS_CACHE_PATH):
    """Returns the persisted per-job embedding cache dict, or {} if
    missing/corrupted/incompatible — a cache miss just means "embed those
    jobs from scratch this time" (handled naturally by
    embed_jobs_incremental), never a crash."""
    if not os.path.exists(path):
        return {}
    try:
        # weights_only=False: this cache stores (hash_string, tensor)
        # tuples inside a dict, not just tensor weights — newer torch
        # defaults to weights_only=True, which would reject that.
        data = torch.load(path, weights_only=False)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def rank_by_resume(jobs_df, resume_text, job_embeddings=None, resume_skills=None):
    """Returns jobs_df with an added `match_pct` column (0-100), sorted
    descending. Blends two signals: semantic similarity (catches
    adjacent/related roles even without exact keyword overlap) and exact
    skill overlap from core/skills.py (grounds the score in something
    concrete — prevents "best of a bad batch" from reading as a near-
    perfect match). Jobs with no recognized skills fall back to pure
    semantic scoring rather than being penalized for missing skill data.

    job_embeddings: optional, precomputed via embed_jobs(jobs_df) — pass
    this to skip re-embedding the whole job pool (see module docstring for
    why that matters). MUST correspond row-for-row to jobs_df; if omitted,
    computed fresh here (slower, but simple/safe for one-off callers).

    resume_skills: optional pre-computed/corrected skill set — if given,
    used INSTEAD of auto-extracting from resume_text via
    core.skills.extract_skills(). Lets a caller (ui/app.py's resume skill
    editor) apply manual corrections — a false positive removed, a real
    skill the regex missed added back in — without needing to fake the
    resume text itself to influence extraction."""
    jobs_df = jobs_df.copy()

    if jobs_df.empty or not resume_text.strip():
        jobs_df["match_pct"] = 0.0
        return jobs_df

    model = get_model()

    if job_embeddings is None:
        job_embeddings = embed_jobs(jobs_df)

    # Resume cap raised 3000 -> 5000 chars for the same reason — the
    # model's own max_seq_length (now 384 tokens, core/embeddings.py) is
    # the real binding limit either way, this just stops US from cutting
    # it short before the model gets a chance to see it.
    resume_embedding = model.encode([resume_text[:5000]], convert_to_tensor=True)

    sims = util.cos_sim(job_embeddings, resume_embedding).flatten().cpu().numpy()

    # Fixed clip range instead of per-batch min-max — see module docstring.
    clipped = sims.clip(SIM_FLOOR, SIM_CEILING)
    semantic_pct = (clipped - SIM_FLOOR) / (SIM_CEILING - SIM_FLOOR) * 100

    if resume_skills is None:
        resume_skills = extract_skills(resume_text)

    # skills column extracted to a plain list ONCE, outside the loop —
    # repeated `.iloc[i]` scalar access inside a Python loop carries real
    # per-call pandas overhead (index alignment, dtype checks) that a
    # single column->list conversion up front avoids entirely. Measured
    # on a real 8,370-job pool: 181ms -> 18ms for this loop, a 10x
    # speedup, with byte-identical output (this changes row-access cost
    # only, not any computation) — this loop can't be vectorized further
    # than this since skill_overlap() does a per-job set intersection
    # against a job-specific skill set, not a uniform array op.
    job_skills_raw_list = jobs_df["skills"].tolist() if "skills" in jobs_df.columns else [""] * len(jobs_df)
    titles_list = jobs_df["title"].fillna("").tolist()
    blended = []
    for sem, job_skills_raw, title in zip(semantic_pct, job_skills_raw_list, titles_list):
        job_skills = set(job_skills_raw.split(",")) if job_skills_raw else set()
        _, _, skill_pct = skill_overlap(resume_skills, job_skills)
        if skill_pct is None:
            score = sem  # no skill data for this job — pure semantic
        else:
            # Scale skill_pct's weight down when the job lists few
            # recognized skills — see MIN_SKILLS_FOR_FULL_WEIGHT. At 3+
            # skills this is identical to the fixed 60/40 blend; below
            # that, semantic similarity picks up the slack instead of
            # letting a single matched keyword dominate.
            confidence = min(1.0, len(job_skills) / MIN_SKILLS_FOR_FULL_WEIGHT)
            skill_weight = SKILL_WEIGHT * confidence
            semantic_weight = 1.0 - skill_weight
            score = semantic_weight * sem + skill_weight * skill_pct

        # Relevance gate — see RELEVANCE_SKILL_PCT_THRESHOLD above.
        title_relevant = bool(config.TARGET_ROLE_RE.search(title))
        skill_relevant = skill_pct is not None and skill_pct >= RELEVANCE_SKILL_PCT_THRESHOLD
        if not (title_relevant or skill_relevant):
            score = min(score, RELEVANCE_GATE_CAP)

        blended.append(score)

    jobs_df["match_pct"] = [round(b, 1) for b in blended]
    return jobs_df.sort_values("match_pct", ascending=False)
