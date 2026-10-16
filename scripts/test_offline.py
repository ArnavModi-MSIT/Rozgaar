"""Run the unittest suite with unmocked HTTP forbidden; no model downloads."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    # Tests explicitly exercise online collector contracts with fake adapters.
    # HF flags prevent accidental weight downloads; HTTP guards fail on any leak.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.pop("JOB_INTEL_OFFLINE", None)
    os.chdir(ROOT)
    with patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected live HTTP in offline tests")) as http, \
         patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected live urllib in offline tests")) as urlopen:
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    if http.call_count or urlopen.call_count:
        raise SystemExit("Offline suite attempted network access")
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
