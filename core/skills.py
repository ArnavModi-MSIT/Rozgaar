"""
Lightweight keyword-based skill extraction — a fixed, curated taxonomy of
common tech skills, matched via word-boundary regex against a text (job
description or resume). Deliberately not ML-based: skills are closed-set
terms (a job either says "Python" or it doesn't), so a curated list is
more reliable here than embeddings/classification, and it's cheap enough
to run inline without caching gymnastics.

Extend SKILLS freely — this list should track the skills that actually
show up in your target roles.
"""

import re

SKILLS = [
    "python", "sql", "java", "javascript", "typescript", "c++", "c#",
    # "r" deliberately excluded — a bare single letter is too ambiguous for
    # keyword matching (e.g. "R&D" would false-positive as the R language;
    # \b can't distinguish that case, unlike the c++/c# fix below which
    # only fails on a skill's OWN trailing punctuation, not context words).
    "power bi", "tableau", "excel", "looker",
    # Added after review feedback flagged these as missing despite being
    # squarely in this project's target roles (Data Analyst / Analytics
    # Engineer / BI) — Power BI's own ecosystem (DAX, Power Query) and the
    # classic enterprise BI/ETL stack weren't represented at all before.
    "dax", "power query", "vba", "ssis", "ssrs", "pl/sql",
    "machine learning", "deep learning", "nlp", "computer vision",
    "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow",
    # Data-science tooling gap flagged by review — these show up
    # constantly in DS/ML job postings and were entirely absent.
    "jupyter", "matplotlib", "seaborn", "statsmodels", "scipy",
    "xgboost", "lightgbm", "catboost", "shap", "mlflow",
    "airflow", "spark", "pyspark", "kafka", "etl", "hadoop",
    "dbt", "databricks", "snowpark", "airbyte", "fivetran",
    "bigquery", "redshift", "synapse", "fabric",
    "delta lake", "iceberg", "hive", "trino", "presto",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
    "react", "node.js", "django", "flask", "fastapi", "rest api", "graphql",
    "postgresql", "mysql", "mongodb", "redis", "snowflake",
    "git", "linux", "agile", "scrum",
    # LLM/GenAI and network-security terms — added after a real, measured
    # false-positive: core/matcher.py's blend showed 80-82% match scores
    # for "LLM DEVELOPER" (needs LLM fine-tuning, Qwen, production model
    # deployment) and "Network Security Engineer" (needs Fortinet, SIEM,
    # Zero Trust, VPN, WAF) against a Data Analyst resume that has NONE of
    # that. Root cause: every one of those postings' actual differentiating
    # requirements was invisible to extract_skills() — completely absent
    # from this list — so skill_overlap() could only ever measure the
    # incidental generic overlap (python/aws), which then produced a
    # falsely-reassuring 2-of-3 "67% skill match", while a resume whose
    # OTHER bullets happen to share adjacent vocabulary (a DRDO internship
    # on "network traffic"/"anomalous activity"; an internship description
    # mentioning a "chatbot") let the semantic half of the blend do the
    # rest. This isn't "track your own target skills" the way the rest of
    # this list is (see module docstring) — it's the opposite: recognizing
    # these lets skill_overlap() correctly report near-zero overlap on
    # roles that don't match, instead of being blind to the very terms
    # that would have revealed the mismatch.
    "llm", "genai", "generative ai", "prompt engineering", "rag",
    "langchain", "fine-tuning", "hugging face", "vector database",
    "firewall", "siem", "zero trust", "vpn", "waf", "sase",
    "penetration testing", "vulnerability assessment", "endpoint security",
    "network security", "cybersecurity", "ids/ips",
    "fortinet", "palo alto", "sonicwall",
]

def build_patterns(extra_skills=None):
    """Builds the regex pattern dict for SKILLS plus any extra custom
    skills (user-added via the UI's skill editor, persisted in
    core/storage.py's custom_skills table — see get_custom_skills()).
    Skills already in the built-in SKILLS list are deduped if also passed
    as extra (case-insensitive) rather than double-compiled."""
    seen = {s.lower() for s in SKILLS}
    all_skills = list(SKILLS)
    for s in (extra_skills or []):
        s = s.strip().lower()
        if s and s not in seen:
            seen.add(s)
            all_skills.append(s)
    return {
        skill: re.compile(rf"(?<![A-Za-z0-9_]){re.escape(skill)}(?![A-Za-z0-9_])", re.I)
        for skill in all_skills
    }


# Plain \b fails on skills that END in a non-word character (c++, c#) —
# \b needs a word-char/non-word-char transition, and skill lists are almost
# always comma/period-terminated ("C++, Python"), so the trailing \b never
# fires against completely ordinary phrasing (confirmed: "C++, Python" and
# "C#." both silently failed to match under the old \b-based pattern).
# Lookarounds anchored on alnum/underscore adjacency instead of \b fix this
# regardless of what character the skill itself starts/ends with.
_PATTERNS = build_patterns()  # built-in SKILLS only — the common case,
# computed once at import so a bare extract_skills(text) call (no custom
# skills involved) stays exactly as cheap as before.


def extract_skills(text, patterns=None):
    """Returns the set of skills found anywhere in text. patterns:
    optional prebuilt dict from build_patterns() — pass this when custom
    skills should be included in matching; omitted, this uses only the
    built-in SKILLS list (unchanged behavior from before custom skills
    existed)."""
    if not text:
        return set()
    patterns = patterns if patterns is not None else _PATTERNS
    return {skill for skill, pattern in patterns.items() if pattern.search(text)}


def skill_overlap(resume_skills, job_skills):
    """Returns (matched, missing, pct). pct is the % of job_skills present
    in resume_skills (0-100). If the job lists no recognized skills at all,
    pct is None — distinct from 0, so callers can tell "no overlap" apart
    from "nothing to compare against"."""
    if not job_skills:
        return set(), set(), None
    matched = resume_skills & job_skills
    missing = job_skills - resume_skills
    pct = round(100 * len(matched) / len(job_skills))
    return matched, missing, pct
