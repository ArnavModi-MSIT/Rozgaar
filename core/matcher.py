"""Local section embeddings plus weighted skills; explanations separate eligibility."""
from sentence_transformers import util

import os
import tempfile
from pathlib import Path

import torch
import pandas as pd

import config
from core.embeddings import get_model, model_cache_identity
from core.skills import extract_skills
from core.match_sections import SECTION_VERSION, job_parts, resume_parts, weighted_skills, eligibility_checks

CHUNK_TOKENS = 192


def _embedding_pipeline_identity():
    return f"{SECTION_VERSION}|tokens={CHUNK_TOKENS}|mean|{model_cache_identity()}"

# Provisional fixed scaling, not calibrated on a labeled job dataset.
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
        + "|" + jobs_df.get("skills", pd.Series("", index=jobs_df.index)).fillna("")
        + "|" + jobs_df.get("location", pd.Series("", index=jobs_df.index)).fillna("")
    ).tolist()
    combined = "\n".join(sorted(parts))
    return hashlib.sha256(combined.encode()).hexdigest()


def _job_content_hash(job_id, title, description, identity=None):
    import hashlib
    identity = identity or _embedding_pipeline_identity()
    return hashlib.sha256(f"{identity}|{job_id}|{title or ''}|{description or ''}".encode()).hexdigest()


def embed_jobs(jobs_df):
    """Embeds every job's title+description, unconditionally — no caching.
    Kept as a simple building block; embed_jobs_incremental (below) is
    what callers should actually use for anything beyond a one-off script,
    since it avoids redoing work for jobs already embedded."""
    if jobs_df.empty:
        return None
    return _encode_section_pairs([job_parts(row.title, row.description) for row in jobs_df.itertuples()])


def _encode_section_pairs(pairs):
    """Token-bounded chunks cover all sections; mean pool each section independently."""
    model = get_model()
    chunks, groups = [], []
    for pair in pairs:
        pair_groups = []
        for text in pair:
            # This pass measures the full section before splitting it. It is
            # never sent to the model directly, so the tokenizer's 512-token
            # warning does not apply here. Keep all tokens for chunking.
            tokens = model.tokenizer.encode(
                text, add_special_tokens=False, truncation=False, verbose=False
            )
            pieces = [model.tokenizer.decode(tokens[i:i+CHUNK_TOKENS], skip_special_tokens=True)
                      for i in range(0, len(tokens), CHUNK_TOKENS)] or [""]
            pair_groups.append((len(chunks), len(chunks) + len(pieces)))
            chunks.extend(pieces)
        groups.append(pair_groups)
    encoded = model.encode(chunks, convert_to_tensor=True, batch_size=64, show_progress_bar=False)
    return torch.stack([torch.stack([encoded[a:b].mean(dim=0) for a,b in group]) for group in groups])


def embed_jobs_incremental(jobs_df, cache=None):
    """Embeds only jobs NOT already covered by `cache` — a dict of
    job_id -> (content_hash, embedding_row_tensor), typically loaded via
    load_embedding_cache(). A cached embedding is reused only when BOTH
    the job_id AND its model/parser/content hash match and its tensor is valid; a job
    whose description changed later without its id changing (e.g. via
    run.py --refetch-oracle) is correctly NOT reused.

    This is the fix for a real problem: the previous whole-pool-hash
    approach invalidated its ENTIRE cache the moment the pool changed by
    even one row — meaning dismissing 2-3 jobs (which shrinks the pool
    once the jobs cache TTL expires) forced a full re-embed of
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
    get_dimension = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
    dimension = get_dimension()
    identity = _embedding_pipeline_identity()
    job_ids = jobs_df["id"].tolist()
    titles = jobs_df["title"].fillna("").tolist()
    descriptions = jobs_df["description"].fillna("").tolist()
    current_ids = set(job_ids)

    rows = [None] * len(job_ids)
    to_embed_idx = []
    to_embed_texts = []
    for i, (jid, title, desc) in enumerate(zip(job_ids, titles, descriptions)):
        h = _job_content_hash(jid, title, desc, identity)
        entry = cache.get(jid)
        if (isinstance(entry, (tuple, list)) and len(entry) == 2 and entry[0] == h
                and isinstance(entry[1], torch.Tensor) and entry[1].is_floating_point()
                and entry[1].layout == torch.strided
                and tuple(entry[1].shape) == (2, dimension) and torch.isfinite(entry[1]).all()):
            rows[i] = entry[1]
        else:
            to_embed_idx.append(i)
            to_embed_texts.append(job_parts(title, desc))

    if to_embed_texts:
        new_embeddings = _encode_section_pairs(to_embed_texts)
        for offset, i in enumerate(to_embed_idx):
            row_tensor = new_embeddings[offset]
            rows[i] = row_tensor
            jid = job_ids[i]
            h = _job_content_hash(jid, titles[i], descriptions[i], identity)
            cache[jid] = (h, row_tensor)

    # Drop cache entries for jobs no longer in the current pool — keeps
    # the persisted cache file from growing unboundedly over time as old
    # jobs eventually get deleted by cleanup_old().
    cache = {jid: entry for jid, entry in cache.items() if jid in current_ids}

    embeddings_tensor = torch.stack(rows)
    return embeddings_tensor, cache, len(to_embed_idx)


DEFAULT_EMBEDDINGS_CACHE_PATH = str(Path(__file__).resolve().parents[1] / "db" / "job_embeddings_cache.pt")


def save_embedding_cache(cache, path=DEFAULT_EMBEDDINGS_CACHE_PATH):
    """Persist the per-job embedding cache to disk across process restarts. cache: dict of job_id -> (content_hash,
    embedding_row_tensor), as produced by embed_jobs_incremental()."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save(cache, stream)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_embedding_cache(path=DEFAULT_EMBEDDINGS_CACHE_PATH):
    """Returns the persisted per-job embedding cache dict, or {} if
    missing/corrupted/incompatible — a cache miss just means "embed those
    jobs from scratch this time" (handled naturally by
    embed_jobs_incremental), never a crash."""
    if not os.path.exists(path):
        return {}
    try:
        # This cache contains only strings, tuples, dicts and tensors.
        # Restricted loading avoids executing arbitrary pickle classes if
        # a local cache file has been replaced or corrupted.
        data = torch.load(path, weights_only=True)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def resume_embedding_key(text):
    import hashlib
    import json
    pair, _ = resume_parts(text)
    value = [_embedding_pipeline_identity(), pair]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def embed_resume(text):
    return _encode_section_pairs([resume_parts(text)[0]])[0]


def rank_by_resume(jobs_df, resume_text, job_embeddings=None, resume_skills=None, resume_embedding=None):
    """Section relevance and weighted skills; eligibility reported independently."""
    jobs_df = jobs_df.copy()
    if jobs_df.empty or not resume_text.strip():
        jobs_df["match_pct"] = 0.0
        jobs_df["match_explanation"] = [{} for _ in range(len(jobs_df))]
        return jobs_df
    if job_embeddings is None:
        job_embeddings = embed_jobs(jobs_df)
    pair, has_evidence = resume_parts(resume_text)
    if resume_embedding is None:
        resume_embedding = embed_resume(resume_text)
    else:
        resume_embedding = resume_embedding.to(job_embeddings.device)
    semantic = []
    for channel in range(2):
        sims = util.cos_sim(job_embeddings[:, channel, :], resume_embedding[channel:channel+1]).flatten().cpu().numpy()
        semantic.append((sims.clip(SIM_FLOOR, SIM_CEILING) - SIM_FLOOR) / (SIM_CEILING-SIM_FLOOR)*100)
    if resume_skills is None:
        resume_skills = extract_skills(resume_text)
    resume_skills = set(resume_skills)
    scores, explanations = [], []
    for i, row in enumerate(jobs_df.itertuples(index=False)):
        stored = {s.strip() for s in (getattr(row, "skills", "") or "").split(",") if s.strip()}
        desc = getattr(row, "description", "") or ""
        skill_pct, required, preferred, all_skills = weighted_skills(desc, stored, resume_skills)
        # Missing project/experience sections are disclosed; do not invent evidence.
        sem = .55 * semantic[0][i] + .45 * semantic[1][i] if has_evidence else semantic[0][i]
        weight = SKILL_WEIGHT * min(1, len(all_skills)/MIN_SKILLS_FOR_FULL_WEIGHT) if skill_pct is not None else 0
        score = (1-weight)*sem + weight*(skill_pct or 0)
        relevant = bool(config.TARGET_ROLE_RE.search(row.title or "")) or (skill_pct is not None and skill_pct >= RELEVANCE_SKILL_PCT_THRESHOLD)
        if not relevant:
            score = min(score, RELEVANCE_GATE_CAP)
        scores.append(round(float(score), 1))
        explanations.append({
            "requirements_relevance": round(float(semantic[0][i]),1),
            "project_responsibility_relevance": round(float(semantic[1][i]),1) if has_evidence else None,
            "weighted_skill_pct": round(skill_pct,1) if skill_pct is not None else None,
            "matched_required": sorted(required & resume_skills),
            "missing_required": sorted(required-resume_skills),
            "matched_preferred": sorted(preferred & resume_skills),
            "matched_skills": sorted(all_skills & resume_skills),
            "relevance_gate_applied": not relevant,
            "note": "Heuristic relevance score, not eligibility or hiring probability. " + ("Projects/work sections compared with responsibilities." if has_evidence else "No separate projects/work sections identified; using resume text as fallback.") + (" Description unavailable; semantic comparison uses the title only." if not desc.strip() else ""),
            "eligibility_checks": eligibility_checks(desc, getattr(row,"location",""), resume_text, required-resume_skills, row.title),
        })
    jobs_df["match_pct"] = scores
    jobs_df["match_explanation"] = explanations
    return jobs_df.sort_values("match_pct", ascending=False)
