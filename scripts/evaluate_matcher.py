"""Compare BM25, MiniLM section-only and current hybrid on identical labels.

Run: python scripts/evaluate_matcher.py examples/matcher_synthetic.json --k 5
Input: {resume_text: string, jobs: [{id,title,description,skills,location,grade}]}
Grades: 0 poor, 1 partial, 2 good relevance. Eligibility is separate.
Keep private labels under ignored db/. No application data or cache is written.
"""
import argparse
import json
import math
import html
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def ranking_metrics(grades, k=10):
    if k < 1:
        raise ValueError("k must be positive")
    top = grades[:k]
    ideal = sorted(grades, reverse=True)[:k]
    def dcg(values):
        return sum((2**grade-1)/math.log2(i+2) for i, grade in enumerate(values))
    return {"precision_at_k": sum(g == 2 for g in top)/len(top) if top else 0,
            "ndcg_at_k": dcg(top)/dcg(ideal) if dcg(ideal) else 0,
            "k": min(k, len(grades))}


def validate(dataset):
    if not isinstance(dataset.get("resume_text"), str) or not dataset["resume_text"].strip():
        raise ValueError("Supply nonempty resume_text")
    jobs = dataset.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Supply at least one labeled job")
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str) or not job["id"].strip():
            raise ValueError("Each job needs a nonempty string id")
        if type(job.get("grade")) is not int or job["grade"] not in (0, 1, 2):
            raise ValueError("Each job needs integer grade 0, 1 or 2")
        for field in ("title", "description", "skills", "location"):
            if field in job and not isinstance(job[field], str):
                raise ValueError(field + " must be a string")
    if len({job["id"] for job in jobs}) != len(jobs):
        raise ValueError("Job IDs must be unique")


def bm25_order(jobs, resume):
    """In-memory FTS5, title weight 2 / description 1; lower rank is better.

    https://www.sqlite.org/fts5.html#the_bm25_function
    Literal tokens and parameterized SQL keep FTS operators out of the query.
    """
    stop = set("a an the and or of to in for with on at as is are was were my i me we our skills education projects experience responsibilities qualifications".split())
    terms = sorted({t for t in re.findall(r"[^\W_]+", resume.lower()) if len(t) > 1 and t not in stop})[:256]
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE postings USING fts5(title, description)")
        def plain(text):
            return re.sub(r"<[^>]*>", " ", html.unescape(text))
        conn.executemany("INSERT INTO postings(rowid,title,description) VALUES(?,?,?)",
                         [(i+1, plain(job.get("title", "")), plain(job.get("description", ""))) for i, job in enumerate(jobs)])
        query = " OR ".join('"' + term + '"' for term in terms)
        scores = dict(conn.execute("SELECT rowid, bm25(postings,2.0,1.0) FROM postings WHERE postings MATCH ?", (query,))) if query else {}
        return sorted(range(len(jobs)), key=lambda i: (scores.get(i+1, 0.0), jobs[i]["id"]))
    finally:
        conn.close()


def evaluate(dataset, k=10, bm25_only=False):
    validate(dataset)
    jobs = sorted(dataset["jobs"], key=lambda job: job["id"])
    resume = dataset["resume_text"]
    def result(order, seconds):
        return {**ranking_metrics([jobs[i]["grade"] for i in order], k),
                "ranking_seconds": round(seconds, 6), "top_ids": [jobs[i]["id"] for i in order[:k]]}
    started = time.perf_counter()
    order = bm25_order(jobs, resume)
    methods = {"bm25": result(order, time.perf_counter()-started)}
    encoding_seconds = None
    if not bm25_only:
        import pandas as pd
        from sentence_transformers import util
        from core.matcher import embed_jobs, embed_resume, rank_by_resume
        from core.match_sections import resume_parts
        frame = pd.DataFrame(jobs)
        for field in ("title", "description", "skills", "location"):
            if field not in frame:
                frame[field] = ""
        started = time.perf_counter()
        vectors, profile = embed_jobs(frame), embed_resume(resume)
        encoding_seconds = round(time.perf_counter()-started, 6)
        started = time.perf_counter()
        sims = [util.cos_sim(vectors[:, c, :], profile[c:c+1]).flatten().cpu().tolist() for c in range(2)]
        evidence = resume_parts(resume)[1]
        dense = [.55*a+.45*b if evidence else a for a, b in zip(*sims)]
        order = sorted(range(len(jobs)), key=lambda i: (-dense[i], jobs[i]["id"]))
        methods["minilm_sections_only"] = result(order, time.perf_counter()-started)
        started = time.perf_counter()
        ranked = rank_by_resume(frame, resume, job_embeddings=vectors, resume_embedding=profile, include_eligibility=False)
        by_id = {job["id"]: i for i, job in enumerate(jobs)}
        methods["current_hybrid"] = result([by_id[jid] for jid in ranked["id"]], time.perf_counter()-started)
    return {"dataset": dataset.get("name", "private labels"), "synthetic": bool(dataset.get("synthetic", False)),
            "jobs": len(jobs), "shared_encoding_seconds": encoding_seconds, "methods": methods,
            "note": "Synthetic examples verify the evaluation path only. Accuracy needs representative human labels and a held-out set. Ranking times exclude shared encoding; first encoding includes model startup. Eligibility is not evaluated."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--bm25-only", action="store_true", help="No model required")
    parser.add_argument("--output", type=Path, help="Optional report; use ignored db/ for private labels")
    args = parser.parse_args()
    try:
        report = evaluate(json.loads(args.labels.read_text(encoding="utf-8")), args.k, args.bm25_only)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
