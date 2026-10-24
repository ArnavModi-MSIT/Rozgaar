"""Build and serve localhost. Collection remains an explicit website action."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.request import urlopen
import webbrowser

import uvicorn
from backend.core.runtime import runtime_identity
from .paths import ROOT, BACKEND, FRONTEND, PYTHON

UI = FRONTEND
DIST = UI / "dist" / "index.html"
URL = "http://127.0.0.1:8000"


def ui_needs_build():
    if not DIST.is_file():
        return True
    watched = [UI / name for name in ("package.json", "package-lock.json", "index.html", "vite.config.ts", "tsconfig.json", "tsconfig.app.json")]
    watched.extend((UI / "src").rglob("*"))
    return any(p.is_file() and p.stat().st_mtime > DIST.stat().st_mtime for p in watched)


def api_status():
    try:
        with urlopen(URL + "/openapi.json", timeout=2) as response:
            if json.load(response).get("info", {}).get("title") != "Rozgaar API":
                return "other"
        with urlopen(URL + "/api/runtime", timeout=2) as response:
            return "ready" if json.load(response) == runtime_identity(ROOT) else "stale"
    except (OSError, ValueError):
        return "down"


def api_ready():
    return api_status() == "ready"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--no-scrape", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not PYTHON.is_file():
        raise RuntimeError("Python environment missing. See README.md for setup.")
    if Path(sys.executable).resolve() != PYTHON.resolve():
        return subprocess.call([str(PYTHON), str(ROOT / "start.py"), *(argv if argv is not None else sys.argv[1:])], cwd=ROOT)
    if not (BACKEND / "api/main.py").is_file() or not (UI / "package.json").is_file():
        raise RuntimeError("Backend or frontend source is missing.")
    if args.check:
        from backend.core.reader_bridge import reader_modules
        reader_modules()
        print(f"Ready. Backend: {BACKEND}; frontend: {UI}; Python: {PYTHON}")
        return 0
    if ui_needs_build():
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise RuntimeError("Node/npm is required to build the frontend.")
        if not (UI / "node_modules").is_dir():
            subprocess.run([npm, "ci"], cwd=UI, check=True)
        subprocess.run([npm, "run", "build"], cwd=UI, check=True)
    status = "ready" if api_ready() else api_status()
    if status in {"stale", "other"}:
        raise RuntimeError("An older Rozgaar backend or another checkout is running on port 8000. Close its API console (Ctrl+C), then launch again.")
    if status == "ready":
        if not args.no_open:
            webbrowser.open(URL)
        print(f"Rozgaar is already running: {URL}")
        return 0
    if not args.no_open:
        def open_when_ready():
            for _ in range(120):
                if api_ready():
                    webbrowser.open(URL)
                    return
                time.sleep(0.5)
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f"Rozgaar: {URL}\nKeep this console open. Ctrl+C stops the platform.\nStart collection from the website.", flush=True)
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8000, log_level="info", access_log=False)
    return 0
