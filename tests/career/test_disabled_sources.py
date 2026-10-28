import unittest
import backend.config as config
from backend.core.collector import PLATFORMS
from scripts.career.company_inventory import inventory,render
class DisabledSourcesTests(unittest.TestCase):
 def test_blocked_sources_are_disabled_and_marked(self):
  for key in ['hrt','expedia']:
   self.assertNotIn(key,dict(PLATFORMS));self.assertIn(key,config.DISABLED_CAREER_SOURCES)
  entries=inventory()
  self.assertNotIn('Hudson River Trading',entries);self.assertNotIn('Expedia Group',entries)
  text=render('27 October 2026')
  self.assertIn('## Disabled sources',text);self.assertIn('HTTP 403',text)
