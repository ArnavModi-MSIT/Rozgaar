"""Conservative evidence labels for exports; never infer candidate eligibility."""
from collections import Counter
import hashlib
import re


def description_quality(text):
    raw_length = len(text or "")
    original = (text or "").strip()
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return "missing"
    if raw_length in {3000, 6000, 10000, 12000} or len(original) in {3000, 6000, 10000, 12000}:
        return "possibly_truncated"
    if len(text) < 120 and "\n" not in original and re.fullmatch(r"Department:\s*[^\n]+", text, re.I):
        return "metadata_only"
    if text.startswith("Innovate in Bengaluru") and not re.search(
        r"responsibilit|qualification|\bskills\b|you will|your role", text, re.I
    ):
        return "boilerplate_only"
    if len(text) < 150:
        return "needs_review"
    return "available"


def annotate_jobs(jobs):
    """Label exact-normalized-text groups without merging requisitions."""
    groups = []
    for job in jobs:
        quality = description_quality(job.get("description"))
        job["description_status"] = quality
        job["assessment_status"] = "unable_to_assess" if quality != "available" else "requires_review"
        normalized = re.sub(r"\s+", " ", job.get("description") or "").strip()
        groups.append(hashlib.sha256(normalized.encode()).hexdigest() if normalized else None)
    counts = Counter(group for group in groups if group)
    for job, group in zip(jobs, groups):
        job["description_group"] = group
        job["same_description_count"] = counts[group] if group else 0
    return {"missing_or_insufficient": sum(j["description_status"] != "available" for j in jobs),
            "distinct_nonempty_description_texts": len(counts),
            "duplicate_comparison": "Whitespace-normalized exact text; shared text does not prove duplicate opportunities."}
