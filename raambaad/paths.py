"""Canonical paths. Keep runtime data separate from source code."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
RUNTIME = ROOT / "runtime"
CAREER_DATA = RUNTIME / "career"
CAREER_DB = CAREER_DATA / "jobs.db"
READER_CODE = ROOT / "url_reader"
READER_RUNTIME = RUNTIME / "reader"
READER_DATA = READER_RUNTIME / "data"
READER_PROFILE = READER_RUNTIME / ".browser-profile"
MODEL_DIR = RUNTIME / "models" / "all-MiniLM-L6-v2"
PYTHON = RUNTIME / "python" / "Scripts" / "python.exe"
