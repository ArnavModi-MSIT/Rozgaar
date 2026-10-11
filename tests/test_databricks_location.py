import unittest
from unittest.mock import patch
from fetchers.standard import fetch_greenhouse
class DatabricksLocationTests(unittest.TestCase):
 def test_foreign_unknown_and_remote_scope(self):
  rows=[dict(id=n,title='Analyst',location={'name':loc},absolute_url='https://example.com/'+str(n),content='Requirements') for n,loc in enumerate(['Madrid','Remote - Spain','EMEA','USCA','Bengaluru, India','Remote - India','Bengaluru, India; Mumbai, India'])]
  with patch('fetchers.standard._get',return_value={'jobs':rows}): jobs=fetch_greenhouse('databricks')
  self.assertEqual([j['source_id'] for j in jobs],['4','5','6'])
if __name__=='__main__': unittest.main()
