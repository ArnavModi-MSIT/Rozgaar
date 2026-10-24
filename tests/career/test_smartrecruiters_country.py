import unittest
from unittest.mock import patch
from backend.fetchers import smartrecruiters as sr
from backend.core.location import is_smartrecruiters_india_location
class SmartRecruitersCountryTests(unittest.TestCase):
 def test_collection_rejects_foreign_and_missing_codes(self):
  jobs=[dict(company='BoschGroup',source_id=str(n),_country_code=c,location=loc,description='') for n,(c,loc) in enumerate([('in','Bangalore, India'),('ro','Cluj-Napoca, CJ, ro'),('','Unknown')])]
  with patch.object(sr,'fetch_smartrecruiters',return_value=jobs),patch.object(sr,'_enrich_company_jobs') as enrich:
   result=sr.collect([{'company_id':'BoschGroup'}])
  self.assertEqual(len(result),1); self.assertEqual(result[0]['source_id'],'0'); self.assertNotIn('_country_code',result[0]); self.assertEqual(len(enrich.call_args.args[0]),1)
 def test_legacy_country_codes(self):
  for loc in ['Cluj-Napoca, CJ, ro','Cluj-Napoca, CJ, ro (Remote)','Remote','Bucharest, Romania','India office, France','']:
   self.assertFalse(is_smartrecruiters_india_location(loc),loc)
  for loc in ['Bengaluru, Karnataka, India','Bangalore, in (Remote)','India']:
   self.assertTrue(is_smartrecruiters_india_location(loc),loc)
if __name__=='__main__': unittest.main()
