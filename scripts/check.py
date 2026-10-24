"""Run local regression checks without starting collection or using saved data."""
import argparse
import compileall
import os
import subprocess
import sys
import unittest
from raambaad.paths import ROOT

BROWSER_FIXTURES = (
    "browser_smoke", "internshala_browser_smoke", "reliability_browser_smoke",
    "dashboard_browser_smoke", "parallel_browser_smoke", "naukri_browser_smoke",
    "instahyre_browser_smoke", "linkedin_posts_browser_smoke", "wellfound_browser_smoke",
    "wellfound_state_browser_smoke", "stall_browser_smoke",
)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="Also run intercepted browser fixtures")
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    for name in ("backend", "url_reader", "raambaad", "scripts"):
        if not compileall.compile_dir(ROOT / name, quiet=1):
            return 1
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():
        return 1
    if args.browser:
        for fixture in BROWSER_FIXTURES:
            subprocess.run([sys.executable, "-m", "tests.reader." + fixture], cwd=ROOT, check=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
