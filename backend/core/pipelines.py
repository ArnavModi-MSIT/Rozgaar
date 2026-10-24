"""Local orchestration for the two existing collectors; no extra server."""
from collections import deque
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import threading
import time

from backend.core.reader_bridge import APP_ROOT, READER_ROOT, reader_modules
from backend.core.separate_pipelines import separate_pipelines
from backend.core.career_exports import latest_export


class PlatformService:
    def __init__(self, db_path, data_dir=None, on_change=lambda: None):
        self.db_path = Path(db_path)
        from rozgaar.paths import READER_DATA
        self.data_dir = Path(data_dir or READER_DATA)
        self.on_change = on_change
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Lock()
        self.data_revision = 0
        self.reader = None
        self.career_process = None
        self.career_thread = None
        self.career_status = "idle"
        self.career_code = None
        self.career_started = None
        self.logs = deque(maxlen=120)
        self.shutdown_event = threading.Event()
        self.separation = None

    def changed(self):
        with self.lock:
            self.data_revision += 1
        self.on_change()

    def manager(self):
        with self.lock:
            if self.reader is None:
                dashboard, _, _ = reader_modules()
                self.reader = dashboard.Manager(data_dir=self.data_dir)
            return self.reader

    def start(self):
        self.shutdown_event.clear()
        self.separation = separate_pipelines(self.db_path, self.data_dir)
        self.changed()

    def close(self):
        self.shutdown_event.set()
        if self.reader:
            self.reader.stop()
            if self.reader.thread:
                self.reader.thread.join(timeout=10)
        self.stop_careers()
        if self.career_thread:
            self.career_thread.join(timeout=10)

    def start_careers(self):
        if os.environ.get("JOB_INTEL_OFFLINE") == "1":
            raise ValueError("Offline mode is enabled. Disable it before collecting new jobs.")
        with self.lock:
            if self.career_process and self.career_process.poll() is None:
                raise RuntimeError("Career collection is already running.")
            # run.py also owns its existing cross-process database lock.
            self.logs.clear()
            env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
            self.career_process = subprocess.Popen(
                [sys.executable, "-u", "-m", "backend.collector"], cwd=APP_ROOT, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            process = self.career_process
            self.career_status, self.career_code = "running", None
            self.career_started = int(time.time())

            def consume():
                try:
                    for line in process.stdout:
                        with self.lock:
                            self.logs.append(line.rstrip()[-1500:])
                    code = process.wait()
                    with self.lock:
                        self.career_code = code
                        self.career_status = "stopped" if self.career_status == "stopping" else ("finished" if code == 0 else "failed")
                finally:
                    process.stdout.close()
                    self.changed()

            self.career_thread = threading.Thread(target=consume, name="career-collector", daemon=True)
            self.career_thread.start()

    def stop_careers(self):
        with self.lock:
            if self.career_process and self.career_process.poll() is None:
                self.career_status = "stopping"
                self.career_process.terminate()

    def snapshot(self):
        counts = {"careers": 0}
        latest = None
        if self.db_path.exists():
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                counts["careers"] = conn.execute("SELECT COUNT(*) FROM jobs WHERE source NOT GLOB 'reader_*'").fetchone()[0]
                latest = latest_export(conn)
        with self.lock:
            career = {"status": self.career_status, "exit_code": self.career_code,
                      "started_at": self.career_started, "logs": list(self.logs)}
        running = bool(self.reader and self.reader.thread and self.reader.thread.is_alive())
        return {"app": "rozgaar", "token": self.token, "data_revision": self.data_revision,
                "mode": "separate", "counts": counts, "latest_export": latest,
                "career": career, "reader_running": running, "separation": self.separation,
                "offline": os.environ.get("JOB_INTEL_OFFLINE") == "1"}
