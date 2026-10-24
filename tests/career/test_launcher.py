import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import raambaad.launcher as start

class LauncherTests(unittest.TestCase):
    def launch(self, args):
        with patch.object(start,"PYTHON",Path(sys.executable)),patch.object(start,"ui_needs_build",return_value=False),patch.object(start,"api_ready",return_value=True),patch.object(start.webbrowser,"open") as opened,patch.object(start.subprocess,"Popen") as spawned,patch.dict(os.environ,{"JOB_INTEL_OFFLINE":"0"}):
            start.main(args)
            opened.assert_called_once_with(start.URL)
            return spawned.call_args_list
    def test_site_only_does_not_spawn_scraper(self):
        self.assertEqual(self.launch(["--no-scrape"]),[])
    def test_default_does_not_spawn_scraper(self):
        self.assertEqual(self.launch([]), [])

    def test_cold_start_spawns_only_api(self):
        with patch.object(start,"PYTHON",Path(sys.executable)), patch.object(start,"ui_needs_build",return_value=False), patch.object(start,"api_ready",return_value=False), patch.object(start,"api_status",return_value="down"), patch.object(start.uvicorn,"run") as serve, patch.object(start.subprocess,"Popen") as spawned:
            start.main(["--no-open"])
            serve.assert_called_once()
            self.assertEqual(serve.call_args.args[0], "backend.api.main:app")
            spawned.assert_not_called()
