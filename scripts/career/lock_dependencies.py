"""Snapshot only this project's dependency closure from a working Windows venv.

Run after intentional upgrades and tests: python scripts/lock_dependencies.py
This does not copy unrelated packages installed in the same environment.
"""
from importlib.metadata import distribution
from pathlib import Path
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOTS = ("requests", "beautifulsoup4", "pandas", "pymupdf", "python-docx",
         "sentence-transformers", "fastapi", "uvicorn", "python-multipart", "httpx", "playwright")


def main():
    if sys.platform != "win32" or sys.version_info[:2] != (3, 10):
        raise SystemExit("Generate this lock on the tested Windows / Python 3.10 environment.")
    found, pending = {}, list(ROOTS)
    while pending:
        name = canonicalize_name(pending.pop())
        if name in found:
            continue
        dist = distribution(name)
        found[name] = dist.version
        for item in dist.requires or []:
            dependency = Requirement(item)
            if dependency.marker is None or dependency.marker.evaluate({"extra": ""}):
                pending.append(dependency.name)
    from rozgaar.paths import ROOT
    target = ROOT / "requirements-lock.txt"
    target.write_text("# Windows x64 / Python 3.10.11; runtime and offline API tests.\n"
                      "# Generated from the tested venv with scripts/lock_dependencies.py.\n"
                      "# Exact versions, not artifact hashes; review intentional upgrades.\n"
                      + "\n".join(f"{name}=={version}" for name, version in sorted(found.items())) + "\n", encoding="utf-8")
    print(f"Locked {len(found)} packages in {target.name}")


if __name__ == "__main__":
    main()
