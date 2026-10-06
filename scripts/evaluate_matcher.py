"""Evaluate local ranking with user-labeled jobs; never writes resume or cache data.

Input JSON: {"resume_text": "...", "jobs": [{"id": "...", "title": "...",
"description": "...", "skills": "sql,python", "location": "India", "grade": 2}]}
Grades: 0 poor relevance, 1 partial, 2 good. Evaluate eligibility separately.
Use at least 30 representative jobs and retain a separate holdout set.
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from core.matcher import rank_by_resume


def ranking_metrics(grades, k=10):
    top = grades[:k]
    ideal = sorted(grades, reverse=True)[:k]
    def dcg(values):
        return sum((2**grade-1)/math.log2(i+2) for i, grade in enumerate(values))
    return {"precision_at_k": sum(g == 2 for g in top)/len(top) if top else 0,
            "ndcg_at_k": dcg(top)/dcg(ideal) if dcg(ideal) else 0,
            "k": min(k, len(grades))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    args = parser.parse_args()
    dataset = json.loads(args.labels.read_text(encoding="utf-8"))
    if not dataset.get("resume_text", "").strip() or not dataset.get("jobs"):
        parser.error("Supply resume_text and at least one labeled job.")
    jobs = dataset["jobs"]
    if any(job.get("grade") not in (0,1,2) for job in jobs):
        parser.error("Each job needs a grade of 0, 1 or 2.")
    if len({job["id"] for job in jobs}) != len(jobs):
        parser.error("Job IDs must be unique.")
    frame = pd.DataFrame(jobs)
    for column in ("skills", "location", "description", "title"):
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("")
    ranked = rank_by_resume(frame, dataset["resume_text"])
    print(json.dumps({"jobs": len(jobs), **ranking_metrics(ranked["grade"].tolist()),
                      "note": "Relevance evaluation only; labels and job sample determine validity."}, indent=2))


if __name__ == "__main__":
    main()
