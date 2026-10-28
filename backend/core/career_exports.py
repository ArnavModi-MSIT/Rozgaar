"""Durable career JSON batches and reversible removal of their exact members."""
from datetime import datetime, timezone
import json
import time
import uuid
from backend.core.description_quality import annotate_jobs


def utc_time(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat() if value is not None else None


def create_export(conn, ids, summaries, filters, limit=100):
    if limit not in (50, 100, 250, 500, 1000) or not 1 <= len(ids) <= limit or len(set(ids)) != len(ids):
        raise ValueError("Choose distinct career jobs within the selected batch size (50, 100, 250, 500 or 1000).")
    slots = ",".join("?" for _ in ids)
    cursor = conn.execute(f"SELECT * FROM jobs WHERE id IN ({slots}) AND dismissed=0 AND source NOT GLOB 'reader_*'", ids)
    columns = [item[0] for item in cursor.description]
    records = {row[0]: dict(zip(columns, row)) for row in cursor}
    if set(records) != set(ids) or not set(ids).issubset(summaries):
        raise ValueError("Some jobs are no longer in the career list. Refresh the list and try again.")
    now = int(time.time())
    batch_id = uuid.uuid4().hex
    filename = f"career-pages-{datetime.now(timezone.utc):%Y-%m-%d-%H%M%S}-{batch_id[:8]}.json"
    jobs = []
    for jid in ids:
        row, summary = records[jid], summaries[jid]
        jobs.append({"id": jid, "title": row["title"], "company": summary["display_company"],
                     "location": row["location"] or "", "url": row["url"], "source": row["source"],
                     "description": row["description"] or "",
                     "description_status": "available" if (row["description"] or "").strip() else "missing",
                     "skills": summary["skills"], "required_experience_years": summary["experience_years"],
                     "preferred_experience_years": summary["preferred_experience_years"],
                     "resume_match_pct": summary["match_pct"], "tracking_status": row["tracking_status"],
                     "posting_status": row["posting_status"], "status_evidence": row["status_evidence"],
                     "first_seen": utc_time(row["first_seen"]), "last_seen": utc_time(row["last_seen"])})
    payload = {"schema_version": 1, "pipeline": "career_pages", "batch_id": batch_id,
               "filename": filename, "exported_at": utc_time(now), "count": len(jobs),
               "selection": {"order": "current_filtered_list", "limit": limit, "filters": filters},
               "note": "Descriptions are exported without truncation from local storage. Source completeness, eligibility and current availability require review.",
               "jobs": jobs}
    payload["description_quality_summary"] = annotate_jobs(jobs)
    with conn:
        conn.execute("INSERT INTO career_exports(batch_id,created_at,filename,payload_json) VALUES(?,?,?,?)",
                     (batch_id, now, filename, json.dumps(payload, ensure_ascii=False)))
        conn.executemany("INSERT INTO career_export_items VALUES(?,?,?)", [(batch_id, jid, index) for index, jid in enumerate(ids)])
    return payload


def export_payload(conn, batch_id):
    row = conn.execute("SELECT payload_json FROM career_exports WHERE batch_id=?", (batch_id,)).fetchone()
    return json.loads(row[0]) if row else None


def latest_export(conn):
    row = conn.execute("""SELECT batch_id,filename,created_at,removed_at FROM career_exports
                          ORDER BY created_at DESC,rowid DESC LIMIT 1""").fetchone()
    if not row:
        return None
    batch_id, filename, created, removed = row
    count, remaining = conn.execute("""SELECT COUNT(*),COALESCE(SUM(CASE WHEN j.dismissed=0 THEN 1 ELSE 0 END),0)
        FROM career_export_items e LEFT JOIN jobs j ON j.id=e.job_id WHERE e.batch_id=?""", (batch_id,)).fetchone()
    return {"batch_id": batch_id, "filename": filename, "created_at": created,
            "removed_at": removed, "count": count, "remaining_count": remaining}


def remove_export(conn, batch_id):
    if not conn.execute("SELECT 1 FROM career_exports WHERE batch_id=?", (batch_id,)).fetchone():
        raise KeyError("JSON batch not found.")
    with conn:
        ids = [row[0] for row in conn.execute("""SELECT j.id FROM career_export_items e JOIN jobs j ON j.id=e.job_id
            WHERE e.batch_id=? AND j.dismissed=0 AND j.source NOT GLOB 'reader_*' ORDER BY e.ordinal""", (batch_id,))]
        conn.executemany("UPDATE jobs SET dismissed=1 WHERE id=?", [(jid,) for jid in ids])
        conn.execute("UPDATE career_exports SET removed_at=COALESCE(removed_at,?) WHERE batch_id=?", (int(time.time()), batch_id))
    return {"removed": len(ids), "ids": ids, "batch_id": batch_id}
