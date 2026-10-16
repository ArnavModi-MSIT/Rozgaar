import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import start

class LauncherTests(unittest.TestCase):
    def launch(self, args):
        with patch.object(start,"PYTHON",Path(sys.executable)),patch.object(start,"ui_needs_build",return_value=False),patch.object(start,"api_ready",return_value=True),patch.object(start.webbrowser,"open") as opened,patch.object(start.subprocess,"Popen") as spawned,patch.dict(os.environ,{"JOB_INTEL_OFFLINE":"0"}):
            start.main(args)
            opened.assert_called_once_with(start.URL)
            return spawned.call_args_list
    def test_site_only_does_not_spawn_scraper(self):
        self.assertEqual(self.launch(["--no-scrape"]),[])
    def test_default_starts_collection(self):
        calls=self.launch([])
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0].args[0],[sys.executable,"run.py"])
