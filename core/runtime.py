"""Identify the checkout and backend source loaded by a local API process."""
import hashlib
from pathlib import Path


def runtime_identity(root):
    root = Path(root).resolve()
    paths = [root / "config.py"]
    paths.extend((root / "api").glob("*.py"))
    paths.extend((root / "core").glob("*.py"))
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return {"root": str(root), "revision": digest.hexdigest()}
