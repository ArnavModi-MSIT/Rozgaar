import unittest
from unittest.mock import patch
import backend.config as config
from backend.fetchers import workday
CFG=next(x for x in config.WORKDAY if x['company']=='ncrvoyix')
def row(i):return dict(title='Software Engineer',externalPath=f'/job/CHENNAI-IND/Engineer_R{i}',locationsText='CHENNAI, IND',bulletFields=[f'R{i}'])
def detail(i):return dict(jobReqId=f'R{i}',title='Software Engineer',location='Chennai',country={'descriptor':'India'},jobDescription='<p>Python responsibilities</p>')
class NcrVoyixTests(unittest.TestCase):
 def test_config_matches_supplied_board_and_filter(self):
  self.assertEqual((CFG['tenant'],CFG['wd_server'],CFG['site']),('ncr','wd1','ext_apac'))
  self.assertEqual(CFG['applied_facets'],{'Location_Country':['c4f78be1a8f14da0ab49ce1162348a5e']})
  self.assertTrue(CFG['fetch_details']);self.assertEqual(config.DISPLAY_NAMES['ncrvoyix'],'NCR Voyix')
 def test_all_27_records_paginate_and_fetch_full_details(self):
  def get(base,tenant,site,path,referer):return detail(path.rsplit('_R',1)[1])
  pages=[dict(total=27,jobPostings=[row(i) for i in range(20)]),dict(total=0,jobPostings=[row(i) for i in range(20,27)])]
  with patch.object(workday,'_post',side_effect=pages) as post,patch.object(workday,'fetch_job_info',side_effect=get),patch.object(workday.time,'sleep'):
   jobs=workday.fetch_workday(CFG)
  self.assertEqual(jobs.status,'ok');self.assertEqual(len(jobs),27)
  self.assertEqual([c.args[1]['offset'] for c in post.call_args_list],[0,20])
  self.assertTrue(all(c.args[1]['appliedFacets']==CFG['applied_facets'] for c in post.call_args_list))
  self.assertTrue(all(j['description'] and 'India' in j['location'] for j in jobs))
 def test_wrong_detail_identity_does_not_attach_body(self):
  with patch.object(workday,'_post',return_value=dict(total=1,jobPostings=[row(1)])),patch.object(workday,'fetch_job_info',return_value=detail(2)):
   jobs=workday.fetch_workday(CFG)
  self.assertEqual(jobs.status,'partial');self.assertEqual(jobs[0]['description'],'')
