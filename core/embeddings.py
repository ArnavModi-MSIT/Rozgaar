"""
Shared sentence-transformer model loader. Both core/classify.py (job
categorization) and core/matcher.py (resume matching) need the same
all-MiniLM-L6-v2 model — this is the single source of truth so the two
don't each load their own separate ~80MB copy into memory within the same
process.
"""

import os

from sentence_transformers import SentenceTransformer

_model = None


def get_model():
    global _model
    if _model is None:
        # PyTorch doesn't always default to using every available core for
        # CPU inference — some environments cap it lower unless told
        # otherwise. But claiming EVERY core (os.cpu_count()) is too
        # aggressive on a machine that's also running Streamlit, SQLite,
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

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        # Default max_seq_length is 256 tokens (~1000-1500 chars) — well
        # below the char-level caps used elsewhere (resume: 5000 chars,
        # job text: 2500 chars in core/matcher.py). Everything past the
        # token limit gets silently dropped by the tokenizer regardless of
        # what text we pass in, meaning a resume's later sections
        # (Projects, usually the most specific tech-stack signal) could be
        # getting cut before the model ever sees them.
        #
        # 512 is this model's actual architectural ceiling (its position
        # embeddings, like most BERT-family models, top out at 512 tokens)
        # — not an arbitrary further bump, this is as far as this single
        # fix can go without hitting a hard wall. Even at 512 tokens
        # (~2000-2500 chars), a long multi-section resume (Education +
        # Experience + Skills + Projects + Certifications) can still
        # exceed that and lose later content — a real, only partially
        # solved limitation. The full fix (embedding each resume section
        # separately and comparing against the relevant part of each job
        # posting, rather than one blob vs. one blob) is a genuinely
        # different, bigger matching architecture, not a config tweak —
        # flagged as a possible future direction, not attempted here.
        _model.max_seq_length = 512
    return _model
