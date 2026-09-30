"""A list of normalized jobs with source-completeness metadata.

Fetchers that do not use this class remain compatible with the collector:
plain lists are treated as successful results.
"""


class CollectionResult(list):
    def __init__(self, jobs=(), *, status="ok", error=""):
        super().__init__(jobs)
        if status not in {"ok", "partial", "skipped"}:
            raise ValueError(f"unsupported collection status: {status}")
        self.status = status
        self.error = error
