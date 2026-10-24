"""Identify all active Python and frontend source for stale-server checks."""
import hashlib
from pathlib import Path

def runtime_identity(root):
    root=Path(root).resolve()
    digest=hashlib.sha256()
    paths=[]
    for name in ("backend","url_reader","raambaad"):
        paths.extend(p for p in (root/name).rglob("*.py") if "__pycache__" not in p.parts)
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return {"root":str(root),"revision":digest.hexdigest()}
