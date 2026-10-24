"""
Job category classification via sentence embeddings — not a trained
classifier, but genuine transformer-based semantic classification: each
category is represented by a short description, each job's title+description
is embedded with the same model, and the category with the highest cosine
similarity wins. Runs locally on CPU, no API key, no per-call cost.

Model: all-MiniLM-L6-v2 (a small distilled BERT-family transformer, ~80MB,
downloaded once and cached by sentence-transformers). Chosen over a larger
model deliberately — fast enough to classify hundreds of jobs per run on a
laptop CPU, which a bigger model wouldn't be.

Two fixes applied after review feedback:

1. Title is now repeated in the embedded text (see _build_text) instead of
   appearing once alongside a much longer description. A short but
   unambiguous title like "Data Analyst" was previously getting diluted by
   a long description that happens to mention adjacent-but-different
   skills (e.g. an analyst role whose description also name-drops "machine
   learning" a few times) — repeating the title gives it proportionally
   more weight in the resulting embedding, biasing toward the title's own
   signal without needing a separate two-stage classifier.

2. "Other" is no longer one of the embedded categories competing on equal
   footing with the real ones. Embedding a description like "a role that
   does not match any specific technical category above" and comparing its
   cosine similarity to job postings doesn't really make semantic sense —
   it's describing an absence, not a topic, so nothing is actually being
   compared against anything coherent. Instead, "Other" is now a threshold
   fallback: if the BEST matching real category's similarity score is
   still below OTHER_THRESHOLD, the job is classified "Other" regardless
   of which category technically scored highest, since none of them
   scored highest with real confidence.
"""

from sentence_transformers import util

from backend.core.embeddings import get_model

_label_embeddings = None

# Extend/edit freely — these are the labels jobs get classified into.
# "Other" is NOT in this dict — see module docstring point 2. It's applied
# as a fallback in classify_jobs() when nothing here scores confidently.
CATEGORIES = {
    "Data Analyst": "analyzing data, building dashboards, SQL, Excel, Power BI, reporting on business metrics",
    "Data Engineer": "building data pipelines, ETL, Airflow, Spark, data warehousing, PySpark",
    "Data Scientist / ML Engineer": "machine learning models, statistics, Python, predictive modeling, AI research",
    "Software Engineer - Backend": "backend development, APIs, databases, server-side systems, Java, Python, Node",
    "Software Engineer - Frontend": "frontend development, UI, React, JavaScript, web interfaces",
    "DevOps / Cloud": "cloud infrastructure, AWS, CI/CD, Kubernetes, Docker, deployment automation",
    "Business / Product": "business analysis, product management, requirements gathering, stakeholder communication",
}

# Below this cosine similarity, even the BEST-scoring real category isn't
# a confident match — classified "Other" instead of forcing a low-
# confidence pick. Same caveat as core/matcher.py's SIM_FLOOR/SIM_CEILING:
# not empirically calibrated against this project's actual observed
# similarity distribution, just a reasonable starting point based on
# general MiniLM-family behavior. Tell me the real distribution once
# you've run this against your data and I'll tune it properly instead of
# guessing again.
OTHER_THRESHOLD = 0.25


def _get_label_embeddings():
    # CATEGORIES never changes at runtime — recomputing this fresh on
    # every classify_jobs() call was pure waste, same reasoning as caching
    # the model itself.
    global _label_embeddings
    if _label_embeddings is None:
        _label_embeddings = get_model().encode(list(CATEGORIES.values()), convert_to_tensor=True)
    return _label_embeddings


def _cap(text, limit=500):
    """Truncate on a whitespace boundary rather than a raw character cut —
    a hard [:limit] slice can land mid-word and feed the model a garbled
    trailing token (not a correctness bug, but a needless quality hit for
    a one-line fix)."""
    text = text[: limit + 20]  # small buffer so the rsplit below has room to work with
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0]


def _build_text(title, desc):
    """Title repeated so it carries more weight in the resulting
    embedding than a single mention would against a much longer
    description — see module docstring point 1."""
    title = title or ""
    return _cap(f"{title}. {title}. {desc or ''}")


def classify_jobs(jobs):
    """jobs: list of (title, description) tuples. Returns a list of category
    strings, same order/length. Batched through the model rather than one
    job at a time — meaningfully faster on CPU for anything beyond a
    handful of jobs."""
    if not jobs:
        return []
    model = get_model()
    labels = list(CATEGORIES.keys())
    label_embeddings = _get_label_embeddings()

    job_texts = [_build_text(title, desc) for title, desc in jobs]
    job_embeddings = model.encode(job_texts, convert_to_tensor=True, batch_size=32, show_progress_bar=False)

    sims = util.cos_sim(job_embeddings, label_embeddings)  # shape (n_jobs, n_labels)
    best = sims.max(dim=1)  # (values, indices) — best score + which category, per job
    results = []
    for score, idx in zip(best.values, best.indices):
        if float(score) < OTHER_THRESHOLD:
            results.append("Other")
        else:
            results.append(labels[int(idx)])
    return results
