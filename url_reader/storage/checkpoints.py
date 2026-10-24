"""Checkpoint validation and atomic writes; preserve saved progress on failure."""
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from url_reader.identity import posting_key, canonical_job_url, source_for_url


def validate_checkpoint(value, search, search_state=None):
    from url_reader.engine import search_signature
    if not isinstance(value, dict) or value.get("schema_version") != 2:
        raise ValueError("Existing output has an unsupported checkpoint schema; file preserved.")
    if search_signature(value.get("search_url", "")) != search_signature(search):
        raise ValueError("Checkpoint belongs to a different search; file preserved.")
    stored_state = value.get("search_state")
    if (stored_state or search_state) and (not isinstance(stored_state, dict) or not isinstance(search_state, dict)
            or not re.fullmatch(r"[a-f0-9]{64}", str(search_state.get("fingerprint", "")))
            or stored_state.get("fingerprint") != search_state.get("fingerprint")):
        raise ValueError("Checkpoint belongs to different Wellfound browser filters; file preserved.")
    for field in ("jobs", "errors"):
        if not isinstance(value.get(field), list) or any(not isinstance(row, dict) for row in value[field]):
            raise ValueError(f"Invalid checkpoint {field}; file preserved.")
    source = source_for_url(search)
    for job in value["jobs"]:
        if any(field in job and not isinstance(job[field], str) for field in ("title", "description", "company", "job_id")):
            raise ValueError("Invalid posting fields in checkpoint; file preserved.")
        key = posting_key(job.get("link"))
        if not key or key[0] != source:
            raise ValueError("Invalid posting in checkpoint; file preserved.")
    progress = value.get("progress")
    if not isinstance(progress, dict):
        raise ValueError("Invalid checkpoint progress; file preserved.")
    if search_signature(progress.get("results_page_url", "")) != search_signature(search):
        raise ValueError("Checkpoint results page has different search filters; file preserved.")
    for field in ("pending_links", "attempted_links"):
        if not isinstance(progress.get(field), list):
            raise ValueError(f"Invalid checkpoint {field}; file preserved.")
        for link in progress[field]:
            key = posting_key(link)
            if not key or key[0] != source or canonical_job_url(link) != link:
                raise ValueError("Invalid job URL in checkpoint; file preserved.")
    if "page_complete" in progress and not isinstance(progress["page_complete"], bool):
        raise ValueError("Invalid page-complete flag; file preserved.")
    if "previously_collected" in progress and (not isinstance(progress["previously_collected"], list)
            or any(not isinstance(key, str) for key in progress["previously_collected"])):
        raise ValueError("Invalid duplicate checkpoint; file preserved.")


def save_result(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    result["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    # Dashboard reads, indexing or security software can briefly deny Windows
    # replacement. Retry the already-written snapshot; never truncate the target.
    delays = (0.05, 0.1, 0.2, 0.4, 0.8, 0.8)
    for attempt in range(len(delays) + 1):
        try:
            temp.replace(path)
            return
        except PermissionError as exc:
            if attempt == len(delays):
                raise PermissionError(
                    f"Checkpoint stayed locked after {attempt + 1} attempts. "
                    f"Previous checkpoint preserved; unsaved snapshot retained at {temp}. Original error: {exc}"
                ) from exc
            time.sleep(delays[attempt])

