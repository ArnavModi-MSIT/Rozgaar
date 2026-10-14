import unittest
from unittest.mock import patch
from fetchers import workday_india,workable,netapp,standard
from fetchers.result import CollectionResult
class NewCompanyBatchTests(unittest.TestCase):
 def test_workday_country_check_excludes_foreign_and_unknown(self):
  cfg=dict(company='browserstack',tenant='browserstack',wd_server='wd3',site='External',verify_global_country=True)
  rows=[dict(title='Engineer',externalPath='/job/'+str(i),bulletFields=[str(i)],locationsText='Mumbai' if i==1 else 'Remote') for i in range(1,4)]
  details=[{'jobPostingInfo':{'location':'Mumbai','country':{'descriptor':'India'},'jobDescription':'<p>Qualifications</p>'}},{'jobPostingInfo':{'country':{'descriptor':'United States'},'jobDescription':'US'}},{'jobPostingInfo':{'jobDescription':'Missing country'}}]
  # Run detail calls serially to associate the mocked detail responses reliably.
  class Serial:
   def __init__(self,**kwargs):pass
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def map(self,fn,items):return map(fn,items)
  with patch.object(workday_india,'post_json',side_effect=[{'jobPostings':rows},{'total':3,'jobPostings':rows}]),patch.object(workday_india,'get_json',side_effect=details),patch.object(workday_india,'ThreadPoolExecutor',Serial):r=workday_india.fetch(cfg)
  self.assertEqual(len(r),1);self.assertEqual(r[0]['location'],'Mumbai, India');self.assertEqual(r.status,'partial')
 def test_f5_distinct_ids_after_non_id_bullet(self):
  cfg=dict(company='f5',tenant='ffive',wd_server='wd5',site='f5jobs',id_bullet_index=1)
  first={'jobPostings':[],'facets':[{'facetParameter':'country','values':[{'id':'in','descriptor':'India'}]}]}
  rows=[dict(title='Engineer',externalPath='/job/'+sid,bulletFields=['0',sid]) for sid in ['RP1','RP2']]
  with patch.object(workday_india,'post_json',side_effect=[first,{'total':2,'jobPostings':rows}]),patch.object(workday_india,'get_json',return_value={'jobPostingInfo':{'jobDescription':'<p>Full description</p>'}}):r=workday_india.fetch(cfg)
  self.assertEqual([j['source_id'] for j in r],['RP1','RP2']);self.assertEqual(r.status,'ok')
 def test_netapp_india_and_actual_next_link(self):
  html='<div id="search-results" data-total-results="16" data-current-page="1"></div><div id="search-results-list"><a data-job-id="1" href="/job/bengaluru/engineer/27600/1"><h3>Engineer</h3><span class="job-location">Bengaluru, India</span></a></div><div class="pagination"><a href="/location/india-jobs/27600/1269750/2/2">Next</a></div>'
  jobs,total,page,nxt=netapp.parse_page(html);self.assertEqual(jobs[0]['title'],'Engineer');self.assertEqual(total,16);self.assertTrue(nxt.endswith('/2/2'))
  with self.assertRaises(RuntimeError):netapp.parse_page(html.replace('Bengaluru, India','Paris, France'))
 def test_workable_empty_is_valid_but_failed_feed_is_not(self):
  with patch.object(workable,'_get',return_value={'name':'Amagi','jobs':[]}):self.assertEqual(workable.collect(['amagi']).status,'ok')
  with patch.object(workable,'_get',return_value=None):
   with self.assertRaises(RuntimeError):workable.fetch_workable('amagi')
 def test_new_global_greenhouse_boards_drop_unknown_locations(self):
  for board in ['appian','couchbaseinc','inmobi','typeface']:
   with patch.object(standard,'_get',return_value={'jobs':[{'title':'Engineer','id':'1','absolute_url':'https://example.com','location':{'name':'EMEA'},'content':'Experience'}]}):self.assertEqual(standard.fetch_greenhouse(board),[])
 def test_inmobi_supported_city_normalization(self):
  with patch.object(standard,'_get',return_value={'jobs':[{'title':'Engineer','id':'1','absolute_url':'https://example.com','location':{'name':'Lucknow'},'content':'Experience'}]}):self.assertEqual(standard.fetch_greenhouse('inmobi')[0]['location'],'Lucknow, India')
if __name__=='__main__':unittest.main()
