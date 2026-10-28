import unittest
from unittest.mock import patch
import backend.config as config
from backend.fetchers import standard
class SprintoTests(unittest.TestCase):
 def test_case_sensitive_registration_and_country_scope(self):
  self.assertEqual(config.LEVER.count('Sprinto'),1);self.assertNotIn('sprinto',config.LEVER)
  def row(id,country,location):return dict(id=id,text='Engineer',country=country,categories={'location':location},hostedUrl='https://jobs.lever.co/Sprinto/'+id,description='Introduction',lists=[{'text':'Qualifications','content':'<p>0-1 years Python</p>'}],additional='Benefits')
  with patch.object(standard,'_get',return_value=[row('1','IN','Bengaluru'),row('2','IN','Remote'),row('3','US','Remote'),row('4','GB','London')]) as get:
   jobs=standard.fetch_lever('Sprinto')
  self.assertEqual([j['source_id'] for j in jobs],['1','2']);self.assertIn('/Sprinto?',get.call_args.args[0]);self.assertIn('India',jobs[1]['location']);self.assertIn('0-1 years Python',jobs[0]['description'])
 def test_full_tail_retained_and_unknown_remote_excluded(self):
  row=dict(id='1',text='Engineer',country='IN',categories={'location':'Remote (India)'},hostedUrl='https://jobs.lever.co/Sprinto/1',description='word '*1500,lists=[{'text':'Qualifications','content':'<p>TAIL 5 years</p>'}])
  with patch.object(standard,'_get',return_value=[row]):jobs=standard.fetch_lever('Sprinto')
  self.assertGreater(len(jobs[0]['description']),6000);self.assertIn('TAIL 5 years',jobs[0]['description'])
  self.assertEqual(standard._lever_location('Sprinto',{'categories':{'location':'Remote'}}),'')
