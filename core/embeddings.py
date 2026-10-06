"""
Shared sentence-transformer model loader. Both core/classify.py (job
categorization) and core/matcher.py (resume matching) need the same
all-MiniLM-L6-v2 model — this is the single source of truth so the two
don't each load their own separate ~80MB copy into memory within the same
process.
"""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

_model = None
MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "all-MiniLM-L6-v2"


def get_model():
    global _model
    if _model is None:
        # PyTorch doesn't always default to using every available core for
        # CPU inference — some environments cap it lower unless told
        # otherwise. But claiming EVERY core (os.cpu_count()) is too
        # aggressive on a machine that's also running FastAPI, SQLite,
        # and network fetchers concurrently — that's CPU contention, not
        # a clean throughput win. Capped at 8 by default (diminishing
        # returns past that for a model this small anyway), overridable
        # via TORCH_NUM_THREADS if you've benchmarked a different number
        # for your machine. os.cpu_count() can return None on some
        # platforms — fall back to leaving torch's own default alone in
        # that case.
        cpu_count = os.cpu_count()
        if cpu_count:
            import torch
            configured = os.environ.get("TORCH_NUM_THREADS")
            num_threads = int(configured) if configured else min(8, cpu_count)
            torch.set_num_threads(num_threads)

        if MODEL_DIR.is_dir():
            model_source = str(MODEL_DIR)
        elif os.environ.get("JOB_INTEL_OFFLINE") == "1":
            raise RuntimeError(
                f"Local embedding model missing at {MODEL_DIR}. "
                "Run `python scripts/download_model.py` while online first."
            )
        else:
            # Backward-compatible first use; the explicit setup script saves
            # a project-local copy for later offline use.
            model_source = "sentence-transformers/all-MiniLM-L6-v2"
        if os.environ.get("JOB_INTEL_OFFLINE") == "1":
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        _model = SentenceTransformer(model_source)
        # Architectural ceiling. The matcher uses 192-token chunks to cover
        # complete selected sections; other callers still use this limit.
        _model.max_seq_length = 512
    return _model
