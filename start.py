"""Start the local Job Intel UI and a collection run on Windows."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
UI = ROOT / "ui-react"
DIST = UI / "dist" / "index.html"
URL = "http://127.0.0.1:8000"


def api_ready():
    try:
        with urlopen(f"{URL}/openapi.json", timeout=2) as response:
            return json.load(response).get("info", {}).get("title") == "Job Intel API"
    except (OSError, ValueError, URLError):
        return False


def ui_needs_build():
    if not DIST.exists():
        return True
    built_at = DIST.stat().st_mtime
    watched = [UI / "package.json", UI / "package-lock.json", UI / "index.html",
               UI / "vite.config.ts", UI / "tsconfig.json", UI / "tsconfig.app.json"]
    watched.extend((UI / "src").rglob("*"))
    return any(path.is_file() and path.stat().st_mtime > built_at for path in watched)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Open Job Intel locally, optionally collecting jobs.")
    parser.add_argument("--no-scrape", action="store_true", help="Open the site using saved jobs without running run.py")
    args = parser.parse_args(argv)
    if os.name != "nt":
        raise RuntimeError("This launcher is for Windows. See README.md for manual commands.")
    os.chdir(ROOT)
    if not PYTHON.exists():
        raise RuntimeError("Missing .venv. Run the one-time Python setup in README.md first.")

    if ui_needs_build():
        if not (UI / "node_modules").exists():
            print("Installing React dependencies (first run)...", flush=True)
            subprocess.run("npm.cmd ci", cwd=UI, check=True, shell=True)
        print("Building React UI...", flush=True)
        subprocess.run("npm.cmd run build", cwd=UI, check=True, shell=True)

    if not api_ready():
        print("Starting API...", flush=True)
        subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        for _ in range(60):
            if api_ready():
                break
            time.sleep(1)
        else:
            raise RuntimeError("API did not start. Check its console for the error.")
    else:
        print("API is already running.", flush=True)

    webbrowser.open(URL)
    if args.no_scrape:
        print("Site only; using saved jobs without collection.", flush=True)
    elif os.environ.get("JOB_INTEL_OFFLINE") == "1":
        print("Offline mode is on; skipping job collection.", flush=True)
    else:
        print("Starting job collection in a separate console...", flush=True)
        subprocess.Popen([str(PYTHON), "run.py"], cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE)
    print(f"Job Intel is open at {URL}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Startup failed: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
