"""One optional local saved resume: parsed text, skills and section embeddings.

No original PDF/DOCX is retained. JSON contains data only; replacement is atomic.
"""
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import torch


from rozgaar.paths import CAREER_DATA
CACHE_PATH = CAREER_DATA / "saved_resume.json"
SCHEMA_VERSION = 1


def parser_signature():
    return hashlib.sha256((Path(__file__).with_name("resume_text.py")).read_bytes()).hexdigest()


def load():
    """A missing/corrupt file is a cache miss, never executable serialized code."""
    try:
        if CACHE_PATH.stat().st_size > 32 * 1024 * 1024:
            return None
        record = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or record.get("schema") != SCHEMA_VERSION:
            return None
        if not re.fullmatch(r"[a-f0-9]{64}", str(record.get("resume_key", ""))):
            return None
        if not isinstance(record.get("text"), str) or not record["text"].strip():
            return None
        if not isinstance(record.get("filename"), str) or not isinstance(record.get("saved_at"), str):
            return None
        if not isinstance(record.get("auto_skills"), list) or not all(isinstance(s, str) for s in record["auto_skills"]):
            return None
        vector = record.get("embedding")
        record["embedding"] = None
        if (isinstance(vector, list) and len(vector) == 2
                and all(isinstance(row, list) for row in vector)
                and 0 < len(vector[0]) == len(vector[1]) <= 4096
                and all(type(n) in (float, int) and math.isfinite(n) for row in vector for n in row)):
            tensor = torch.tensor(vector, dtype=torch.float32)
            if torch.isfinite(tensor).all():
                record["embedding"] = tensor
        return record
    except (OSError, ValueError, TypeError, OverflowError):
        return None


def save(record):
    """Keep the prior saved copy intact if writing the replacement fails."""
    record = {**record, "schema": SCHEMA_VERSION,
              "saved_at": datetime.now(timezone.utc).isoformat()}
    filename = record["filename"].replace("\\", "/").rsplit("/", 1)[-1]
    record["filename"] = filename[:255] or "resume"
    vector = record.get("embedding")
    if vector is not None:
        record["embedding"] = vector.detach().cpu().tolist()
    content = json.dumps(record, ensure_ascii=False, allow_nan=False)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CACHE_PATH.parent,
                                         prefix="saved_resume.", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(content)
        os.replace(temporary, CACHE_PATH)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def info():
    record = load()
    return ({"resume_key": record["resume_key"], "filename": record["filename"],
             "saved_at": record["saved_at"], "word_count": len(record["text"].split())}
            if record else None)


def delete():
    CACHE_PATH.unlink(missing_ok=True)
